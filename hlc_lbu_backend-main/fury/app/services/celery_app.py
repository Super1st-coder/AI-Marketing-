"""Celery application factory."""
from celery import Celery
from core.config import settings

celery_app = Celery(
    "fury",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["services.job_runner_service", "services.persona_job_runner_service"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    broker_transport_options={
        'visibility_timeout': 18000
    },
    # HL-2630: hard bound on total task wall-time. A hung image generation (Gemini/SDK stall)
    # was observed hanging 27+ min holding the worker; in-code asyncio timeouts could NOT
    # cancel the blocking call inside asyncio.to_thread, so they never fired. The soft limit
    # raises SoftTimeLimitExceeded (SIGALRM on the worker's main thread, which is sitting in
    # loop.run_until_complete) — it propagates out and hits the existing retry path in
    # run_pipeline_phase1. The hard limit is the last-resort backstop (worker killed; not
    # redelivered, since task_reject_on_worker_lost=False).
    #
    # 420s was TOO TIGHT: a healthy n=3 run (≈33 image generations at concurrency 2) legitimately
    # needs >7 min while Gemini is responding normally, so the soft limit fired mid-flight on a
    # successful run and forced a retry (observed job 6ad7dd6e, all Gemini responses OK). Sized to
    # cover the largest normal Phase1 (n=3) with margin; a genuine infinite hang is still bounded.
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    # HL-2630: keep acks_late so a graceful redeploy re-runs an interrupted job, but do
    # NOT re-queue a job whose worker was KILLED (SIGKILL/OOM). With reject_on_worker_lost
    # True, an OOM'd image-gen task redelivered forever (observed 48× on one job), clogging
    # the queue and never surfacing a failure. False makes such a job fail cleanly so it can
    # be re-run deliberately once memory is addressed (see IMAGE_GEN_MAX_CONCURRENCY).
    task_reject_on_worker_lost=False,
    # PROTECCIÓN AJUSTADA A 4GB TOTALES (Valores en Kilobytes):
    # Cada proceso se reiniciará si acumula más de 1.2 GB residuales
    worker_max_memory_per_child=settings.CELERY_WORKER_MAX_MEMORY_PER_CHILD, 
    worker_max_tasks_per_child=settings.CELERY_WORKER_MAX_TASKS_PER_CHILD, # Reiniciar más seguido ayuda a liberar RAM rápido
)
