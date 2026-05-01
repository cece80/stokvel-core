"""
KYC/FICA Compliance Module
============================
Implements Know Your Customer (KYC) requirements per South Africa's
Financial Intelligence Centre Act (FICA), Act 38 of 2001.

Requirements for stokvel signatories:
1. Valid SA ID document or passport
2. Proof of residential address (not older than 3 months)

The platform enforces:
- Document submission tracking
- Verification workflow
- Expiry monitoring (proof of address must be refreshed)
- Audit trail for all KYC actions
"""

from datetime import date, datetime, timedelta
from typing import Optional, List, Tuple
from .models import (
    User, KYCDocument, KYCStatus, DocumentType,
    StokvelMembership, StokvelRole
)
from .validators import validate_sa_id_number, SAIDValidationError


# ──────────────────────────────────────────────
# KYC Verification Flow
# ──────────────────────────────────────────────

PROOF_OF_ADDRESS_MAX_AGE_DAYS = 90  # 3 months per FICA


def start_kyc_verification(user: User) -> dict:
    """
    Determine what KYC documents are needed for a user.
    
    Returns:
        Dictionary with required documents and current status
    """
    required_docs = [
        {
            "type": DocumentType.SA_ID_DOCUMENT.value,
            "description": "South African ID document (smart card or book) or valid passport",
            "required": True,
        },
        {
            "type": DocumentType.PROOF_OF_ADDRESS.value, 
            "description": "Proof of residential address (utility bill, bank statement - not older than 3 months)",
            "required": True,
        },
    ]
    
    return {
        "user_id": user.id,
        "current_status": user.kyc_status.value,
        "required_documents": required_docs,
        "message": "Please submit the required documents to complete KYC verification",
    }


def submit_kyc_document(
    user: User,
    document_type: DocumentType,
    document_number: Optional[str] = None,
    document_url: Optional[str] = None,
    document_date: Optional[date] = None,
) -> Tuple[KYCDocument, dict]:
    """
    Submit a KYC document for verification.
    
    Args:
        user: The user submitting the document
        document_type: Type of document
        document_number: ID number or passport number
        document_url: URL to uploaded document image/PDF
        document_date: Date on the document (for proof of address)
        
    Returns:
        Tuple of (KYCDocument, validation_result)
    """
    validation_errors = []
    
    # Validate SA ID number if provided
    if document_type in [DocumentType.SA_ID_DOCUMENT, DocumentType.SA_ID_CARD]:
        if document_number:
            try:
                id_info = validate_sa_id_number(document_number)
                # Update user's SA ID number
                user.sa_id_number = document_number
            except SAIDValidationError as e:
                validation_errors.append(str(e))
    
    # Validate proof of address freshness
    if document_type == DocumentType.PROOF_OF_ADDRESS:
        if document_date:
            age_days = (date.today() - document_date).days
            if age_days > PROOF_OF_ADDRESS_MAX_AGE_DAYS:
                validation_errors.append(
                    f"Proof of address is {age_days} days old. "
                    f"Must be less than {PROOF_OF_ADDRESS_MAX_AGE_DAYS} days (3 months) per FICA requirements."
                )
    
    if validation_errors:
        return None, {
            "success": False,
            "errors": validation_errors,
        }
    
    # Create document record
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
    
    # Update user KYC status
    user.kyc_status = KYCStatus.DOCUMENTS_SUBMITTED
    
    return doc, {
        "success": True,
        "document_id": doc.id,
        "message": "Document submitted for verification",
    }


def verify_kyc_document(
    doc: KYCDocument,
    verified_by: str,
    approved: bool,
    rejection_reason: Optional[str] = None,
) -> dict:
    """
    Admin action: Verify or reject a KYC document.
    
    Args:
        doc: The document to verify
        verified_by: Admin user ID who is verifying
        approved: Whether to approve or reject
        rejection_reason: Reason for rejection (if rejected)
    """
    doc.verified_by = verified_by
    doc.verified_at = datetime.utcnow()
    
    if approved:
        doc.is_verified = True
        return {
            "success": True,
            "status": "verified",
            "message": "Document verified successfully",
        }
    else:
        doc.rejection_reason = rejection_reason or "Document does not meet requirements"
        return {
            "success": True,
            "status": "rejected",
            "reason": doc.rejection_reason,
            "message": "Document rejected. User will be notified to resubmit.",
        }


def check_kyc_completeness(
    user: User,
    documents: List[KYCDocument],
) -> Tuple[bool, dict]:
    """
    Check if a user has completed all required KYC steps.
    
    For stokvel signatories, both ID and proof of address are required.
    
    Returns:
        Tuple of (is_complete, details)
    """
    has_id = any(
        d.is_verified and d.document_type in [
            DocumentType.SA_ID_DOCUMENT,
            DocumentType.SA_ID_CARD,
            DocumentType.PASSPORT,
        ]
        for d in documents
    )
    
    has_address = any(
        d.is_verified 
        and d.document_type == DocumentType.PROOF_OF_ADDRESS
        and d.expires_at 
        and d.expires_at >= date.today()
        for d in documents
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
    
    return is_complete, {
        "is_complete": is_complete,
        "has_id_document": has_id,
        "has_proof_of_address": has_address,
        "missing_documents": missing,
        "kyc_status": user.kyc_status.value,
    }


def check_signatory_kyc_compliance(
    memberships: List[StokvelMembership],
    users: dict,  # user_id -> User mapping
    documents: dict,  # user_id -> List[KYCDocument] mapping
) -> dict:
    """
    Check if all stokvel signatories meet KYC requirements.
    
    Per SA banking requirements, all signatories must be KYC-verified.
    Minimum 3 signatories required.
    """
    signatories = [m for m in memberships if m.is_signatory and m.is_active]
    
    if len(signatories) < 3:
        return {
            "compliant": False,
            "error": f"Minimum 3 signatories required. Currently have {len(signatories)}.",
            "signatories_count": len(signatories),
        }
    
    non_compliant = []
    for sig in signatories:
        user = users.get(sig.user_id)
        user_docs = documents.get(sig.user_id, [])
        if user:
            is_complete, details = check_kyc_completeness(user, user_docs)
            if not is_complete:
                non_compliant.append({
                    "user_id": sig.user_id,
                    "name": user.full_name,
                    "missing": details["missing_documents"],
                })
    
    return {
        "compliant": len(non_compliant) == 0,
        "total_signatories": len(signatories),
        "verified_signatories": len(signatories) - len(non_compliant),
        "non_compliant_signatories": non_compliant,
    }
