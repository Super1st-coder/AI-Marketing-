"""Custom exceptions"""
from typing import Optional, Dict, Any


class FuryException(Exception):
    """Base exception for Fury API"""
    
    def __init__(
        self,
        message: str,
        code: str = "FURY_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class StrapiException(FuryException):
    """Strapi related exceptions"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="STRAPI_ERROR",
            status_code=500,
            details=details
        )


class ValidationException(FuryException):
    """Validation exceptions"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class AIException(FuryException):
    """AI/LLM related exceptions"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AI_ERROR",
            status_code=500,
            details=details
        )


class VectorStoreException(FuryException):
    """Vector store related exceptions"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VECTORSTORE_ERROR",
            status_code=500,
            details=details
        )


# ---------------------------------------------------------------------------
# Ad-variant image-edit pipeline (services/job_runner_service.py)
# ---------------------------------------------------------------------------


class AdVariantImageEditError(FuryException):
    """Base de errores del pipeline de edición de imagen de variante.

    Atributos de clase: ``code``, ``status_code``, ``step``, ``retryable``.
    ``__reduce__`` explícito para que pickle (Celery) conserve clase, message,
    code, status_code y details (Req 12.8). ``args == (message,)``, compatible
    con la reconstrucción ``cls(*args)`` del backend JSON de Celery.
    """

    code: str = "AD_VARIANT_IMAGE_EDIT_ERROR"
    status_code: int = 500
    step: str = ""
    retryable: bool = True

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=type(self).code,
            status_code=type(self).status_code,
            details=details,
        )

    def __reduce__(self):
        return (self.__class__, (self.message, self.details))


class BaseImageFetchError(AdVariantImageEditError):
    """Red/timeout/no-2xx/cuerpo inválido en get_ad_variant_image (Req 4.4)."""

    code = "AD_VARIANT_BASE_IMAGE_FETCH_FAILED"
    status_code = 502
    step = "fetch_base_image"
    retryable = True


class BaseImageMismatchError(AdVariantImageEditError):
    """El id devuelto por Sinergia no coincide con id_base_image (Req 4.9)."""

    code = "AD_VARIANT_BASE_IMAGE_ID_MISMATCH"
    status_code = 409
    step = "fetch_base_image"
    retryable = False


class BaseImageUrlMissingError(AdVariantImageEditError):
    """La Base_Image no tiene url (ausente, None o en blanco) (Req 5.3)."""

    code = "AD_VARIANT_BASE_IMAGE_URL_MISSING"
    status_code = 422
    step = "download"
    retryable = False


class BaseImageDownloadError(AdVariantImageEditError):
    """Fallo descargando el binario de la Base_Image (Req 5.4, 5.5)."""

    code = "AD_VARIANT_BASE_IMAGE_DOWNLOAD_FAILED"
    status_code = 502
    step = "download"
    retryable = True


class ImageEditingFailedError(AdVariantImageEditError):
    """edit_image_variations no devolvió ninguna variación (Req 7.9, 7.10)."""

    code = "AD_VARIANT_IMAGE_EDITING_FAILED"
    status_code = 502
    step = "image_editing"
    retryable = True


class VariationUploadFailedError(AdVariantImageEditError):
    """Fallaron todas las subidas de variaciones a Sinergia (Req 9.8)."""

    code = "AD_VARIANT_IMAGE_UPLOAD_FAILED"
    status_code = 502
    step = "upload"
    retryable = True


class VariationUrlResolutionError(VariationUploadFailedError):
    """Ninguna Uploaded_Image resolvió su url en resolve_urls (Req 14.7)."""

    code = "AD_VARIANT_IMAGE_URL_RESOLUTION_FAILED"
    status_code = 502
    step = "resolve_urls"
    retryable = True


class EditJobEnqueueError(AdVariantImageEditError):
    """apply_async falló al encolar el job de edición (Req 2.5)."""

    code = "AD_VARIANT_IMAGE_EDIT_ENQUEUE_FAILED"
    status_code = 503
    step = "enqueue"


class EditPipelineInternalError(AdVariantImageEditError):
    """Excepción no-Fury durante el run-local del pipeline (Req 12.3)."""

    code = "INTERNAL_ERROR"
    status_code = 500
    step = ""


# ---------------------------------------------------------------------------
# Adset creative diversity (services/job_runner_service.py, Diversity_Path)
# ---------------------------------------------------------------------------

class AdsetCreativeDiversityError(FuryException):
    """Fallo de job del Diversity_Path (p.ej. Adset sin anclas, Req 3.11).

    ``__reduce__`` explícito para que pickle (Celery) conserve clase, message,
    code, status_code y details.
    """

    code: str = "ADSET_DIVERSITY_ERROR"
    status_code: int = 500

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=type(self).code,
            status_code=type(self).status_code,
            details=details,
        )

    def __reduce__(self):
        return (self.__class__, (self.message, self.details))
