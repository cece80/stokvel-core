from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from app.models.user import User, KYCDocument, KYCStatus, DocumentType
from app.core.validation import validate_sa_id
from app.core.exceptions import ValidationError

PROOF_OF_ADDRESS_MAX_AGE_DAYS = 90

class KYCService:
    @staticmethod
    def submit_kyc(
        user: User,
        document_type: DocumentType,
        document_number: Optional[str] = None,
        document_url: Optional[str] = None,
        document_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        errors = []
        if document_type in [DocumentType.SA_ID_DOCUMENT, DocumentType.SA_ID_CARD]:
            if document_number:
                try:
                    validate_sa_id(document_number)
                    user.sa_id_number = document_number
                except ValidationError as e:
                    errors.append(str(e))
        if document_type == DocumentType.PROOF_OF_ADDRESS:
            if document_date:
                age_days = (date.today() - document_date).days
                if age_days > PROOF_OF_ADDRESS_MAX_AGE_DAYS:
                    errors.append(
                        f"Proof of address is {age_days} days old. Must be less than {PROOF_OF_ADDRESS_MAX_AGE_DAYS} days (3 months) per FICA requirements."
                    )
        if errors:
            return {"success": False, "errors": errors}
        doc = KYCDocument(
            user_id=user.id,
            document_type=document_type,
            document_number=document_number,
            document_url=document_url,
            document_date=document_date,
            expires_at=(
                document_date + timedelta(days=PROOF_OF_ADDRESS_MAX_AGE_DAYS)
                if document_date and document_type == DocumentType.PROOF_OF_ADDRESS
                else None
            ),
        )
        user.kyc_status = KYCStatus.DOCUMENTS_SUBMITTED
        # Save to DB (stub)
        return {"success": True, "document_id": doc.id, "message": "Document submitted for verification"}

    @staticmethod
    def verify_kyc(
        doc: KYCDocument,
        verified_by: str,
        approved: bool,
        rejection_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        doc.verified_by = verified_by
        doc.verified_at = datetime.utcnow()
        if approved:
            doc.is_verified = True
            # Save to DB (stub)
            return {"success": True, "status": "verified", "message": "Document verified successfully"}
        else:
            doc.rejection_reason = rejection_reason or "Document does not meet requirements"
            # Save to DB (stub)
            return {"success": True, "status": "rejected", "reason": doc.rejection_reason, "message": "Document rejected. User will be notified to resubmit."}

    @staticmethod
    def get_kyc_status(user: User, documents: List[KYCDocument]) -> Dict[str, Any]:
        has_id = any(
            d.is_verified and d.document_type in [
                DocumentType.SA_ID_DOCUMENT,
                DocumentType.SA_ID_CARD,
                DocumentType.PASSPORT,
            ] for d in documents
        )
        has_address = any(
            d.is_verified and d.document_type == DocumentType.PROOF_OF_ADDRESS and d.expires_at and d.expires_at >= date.today() for d in documents
        )
        is_complete = has_id and has_address
        if is_complete:
            user.kyc_status = KYCStatus.VERIFIED
            user.kyc_verified_at = datetime.utcnow()
        missing = []
        if not has_id:
            missing.append("ID document or passport")
        if not has_address:
            missing.append("Valid proof of address (< 3 months old)")
        return {
            "is_complete": is_complete,
            "has_id_document": has_id,
            "has_proof_of_address": has_address,
            "missing_documents": missing,
            "kyc_status": user.kyc_status.value,
        }
