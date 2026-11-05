
import base64
import json
import logging
import os
from datetime import date, datetime, timezone

import functions_framework
import google.cloud.logging
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import billing_v1

_log_client = google.cloud.logging.Client()
_log_client.setup_logging()

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())


def _parse_env_list(env_var: str) -> list[str]:
    raw = os.environ.get(env_var, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _is_before_active_from() -> bool:
    active_from_str = os.environ.get("ACTIVE_FROM", "").strip()
    if not active_from_str:
        return False
    active_from = date.fromisoformat(active_from_str)
    return date.today() < active_from


def _resolve_target_projects(billing_client: billing_v1.CloudBillingClient) -> list[str]:
    explicit_projects = _parse_env_list("PROJECT_IDS")
    if explicit_projects:
        logger.info("MODO 1 – Lista de %d proyecto(s).", len(explicit_projects))
        return explicit_projects

    billing_account_id = os.environ.get("BILLING_ACCOUNT_ID", "").strip()
    if not billing_account_id:
        raise EnvironmentError(
            "Debes definir PROJECT_IDS o BILLING_ACCOUNT_ID en las variables de entorno."
        )

    excluded = set(_parse_env_list("EXCLUDED_PROJECT_IDS"))
    if excluded:
        logger.info("MODO 2 – Todos los proyectos EXCEPTO: %s", excluded)
    else:
        logger.info("MODO 2 – Todos los proyectos de la billing account.")

    all_projects: list[str] = []
    try:
        pager = billing_client.list_project_billing_info(
            name=f"billingAccounts/{billing_account_id}"
        )
        for project_info in pager:
            proj_id = project_info.project_id
            if proj_id and proj_id not in excluded:
                all_projects.append(proj_id)
            elif proj_id in excluded:
                logger.info("Proyecto exento: %s", proj_id)
    except GoogleAPICallError as e:
        logger.error("Error al listar proyectos de la billing account: %s", e)
        raise

    logger.info("Total proyectos elegibles: %d", len(all_projects))
    return all_projects


def _is_billing_enabled(client: billing_v1.CloudBillingClient, project_id: str) -> bool:
    try:
        info = client.get_project_billing_info(name=f"projects/{project_id}")
        return info.billing_enabled
    except GoogleAPICallError as e:
        logger.error("Error al verificar billing para %s: %s", project_id, e)
        raise


def _disable_billing(client: billing_v1.CloudBillingClient, project_id: str) -> None:
    try:
        client.update_project_billing_info(
            name=f"projects/{project_id}",
            project_billing_info=billing_v1.ProjectBillingInfo(billing_account_name=""),
        )
        logger.info("Billing deshabilitado: %s", project_id)
    except GoogleAPICallError as e:
        logger.error("Error al deshabilitar billing para %s: %s", project_id, e)
        raise


def _disable_billing_for_all_targets() -> tuple[list[str], list[str]]:
    billing_client = billing_v1.CloudBillingClient()
    project_ids = _resolve_target_projects(billing_client)

    if not project_ids:
        logger.warning("No hay proyectos elegibles para deshabilitar billing.")
        return [], []

    errors: list[str] = []
    processed: list[str] = []

    for pid in project_ids:
        logger.info("Procesando proyecto: %s", pid)
        try:
            if not _is_billing_enabled(billing_client, pid):
                logger.info("Billing ya deshabilitado en %s. Saltando.", pid)
                continue
            _disable_billing(billing_client, pid)
            processed.append(pid)
        except GoogleAPICallError as e:
            errors.append(f"{pid}: {e}")

    return processed, errors



def _get_current_monthly_spend(project_id: str, billing_account_id: str) -> float:
    from google.cloud import monitoring_v3

    monitoring_client = monitoring_v3.MetricServiceClient()

    now = datetime.now(timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    interval = monitoring_v3.TimeInterval(
        end_time={"seconds": int(now.timestamp()), "nanos": 0},
        start_time={"seconds": int(start_of_month.timestamp()), "nanos": 0},
    )

    filter_str = 'metric.type="billing.googleapis.com/billing/monthly_cost"'

    results = monitoring_client.list_time_series(
        request={
            "name": f"billingAccounts/{billing_account_id}",
            "filter": filter_str,
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        }
    )

    total = 0.0
    per_project: dict[str, float] = {}

    for ts in results:
        if ts.points:
            amount = ts.points[0].value.double_value
            proj   = ts.resource.labels.get("project_id", "unknown")
            per_project[proj] = per_project.get(proj, 0.0) + amount
            total += amount

    logger.info(
        "[GASTO DEL MES] Total: %.2f MXN | Proyectos activos: %d | "
        "Periodo: %s–hoy",
        total,
        len(per_project),
        start_of_month.strftime("%Y-%m-%d"),
    )

    for proj, amount in sorted(per_project.items(), key=lambda x: x[1], reverse=True):
        logger.info("  ├─ %-45s  %9.2f MXN", proj, amount)

    return total


@functions_framework.http
def check_billing_scheduler(request):
    project_id         = os.environ.get("PROJECT_ID", "").strip()
    billing_account_id = os.environ.get("BILLING_ACCOUNT_ID", "").strip()
    budget_amount      = float(os.environ.get("BUDGET_AMOUNT", "0") or "0")

    if not project_id or not billing_account_id or budget_amount <= 0:
        msg = (
            "ERROR: Faltan variables de entorno requeridas: "
            "PROJECT_ID, BILLING_ACCOUNT_ID, BUDGET_AMOUNT."
        )
        logger.error(msg)
        return msg, 500

    try:
        current_spend = _get_current_monthly_spend(project_id, billing_account_id)
    except Exception as e:
        msg = f"ERROR al consultar Cloud Monitoring: {e}"
        logger.error(msg)
        return msg, 500

    spend_pct = (current_spend / budget_amount * 100) if budget_amount > 0 else 0.0
    logger.info(
        "[PRESUPUESTO] %.2f / %.2f MXN (%.1f%% usado) | Límite activo: %s",
        current_spend,
        budget_amount,
        spend_pct,
        os.environ.get("ACTIVE_FROM", "siempre"),
    )

    if _is_before_active_from():
        active_from_str = os.environ.get("ACTIVE_FROM", "")
        msg = f"SKIPPED: Antes de ACTIVE_FROM ({active_from_str}). Monitoreo OK, sin acción."
        logger.info(msg)
        return msg, 200

    if current_spend < budget_amount:
        msg = f"OK: {spend_pct:.1f}% del presupuesto usado. Sin acción."
        logger.info(msg)
        return msg, 200

    logger.warning(
        "ALERTA CRÍTICA: Gasto %.2f MXN >= límite %.2f MXN (%.1f%%). "
        "Iniciando desactivación de billing...",
        current_spend, budget_amount, spend_pct,
    )

    try:
        processed, errors = _disable_billing_for_all_targets()
    except EnvironmentError as e:
        logger.error(str(e))
        return f"ERROR: {e}", 500

    if errors:
        msg = f"PARTIAL ERROR: Falló en {len(errors)} proyecto(s): {'; '.join(errors)}"
        logger.error(msg)
        return msg, 500

    msg = f"OK: Billing deshabilitado en {len(processed)} proyecto(s): {processed}"
    logger.info(msg)
    return msg, 200


# ── Entry point Pub/Sub / CloudEvent  ─────────────────────────────────
@functions_framework.cloud_event
def stop_billing(cloud_event) -> None:
    try:
        raw_data = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
        budget_data: dict = json.loads(raw_data)
    except (KeyError, json.JSONDecodeError, ValueError) as e:
        logger.error("No se pudo parsear el mensaje de Pub/Sub: %s", e)
        return

    cost_amount: float    = float(budget_data.get("costAmount", 0))
    budget_amount: float  = float(budget_data.get("budgetAmount", 0))
    budget_display_name   = budget_data.get("budgetDisplayName", "N/A")
    alert_threshold: float = float(budget_data.get("alertThresholdExceeded", 0))

    logger.info(
        "Budget Alert | '%s' | Costo: %.2f | Límite: %.2f | Threshold: %.0f%%",
        budget_display_name, cost_amount, budget_amount, alert_threshold * 100,
    )

    active_from_str    = os.environ.get("ACTIVE_FROM", "").strip()
    cost_interval_start = budget_data.get("costIntervalStart", "")
    if active_from_str and cost_interval_start:
        billing_period = date.fromisoformat(cost_interval_start[:10])
        active_from    = date.fromisoformat(active_from_str)
        if billing_period < active_from:
            logger.info(
                "Periodo %s < ACTIVE_FROM %s. Sin acción.",
                billing_period, active_from,
            )
            real_cost = cost_amount - 1314000
            cost_amount = real_cost
            logger.info("Reemplazado a costo real: %.2f MXN", cost_amount)
            if real_cost < 2000:
                alert_threshold = 0.5
                logger.info("Reemplazado alerta threshold: %.2f threshold", alert_threshold)
            #return

    if alert_threshold < 1.0:
        logger.info("Threshold %.0f%% < 100%%. Sin acción.", alert_threshold * 100)
        return

    logger.warning("ALERTA CRÍTICA: Threshold %.0f%% alcanzado.", alert_threshold * 100)

    try:
        processed, errors = _disable_billing_for_all_targets()
    except EnvironmentError as e:
        logger.error(str(e))
        return

    if errors:
        raise RuntimeError(
            f"Falló desactivación en {len(errors)} proyecto(s): {'; '.join(errors)}"
        )

    logger.info("Proceso finalizado. Proyectos procesados: %s", processed)
