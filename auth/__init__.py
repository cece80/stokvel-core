"""
Stokvel Auth Module
===================
Authentication, authorization, and KYC/FICA compliance for the Stokvel OS platform.

Based on Saleor Core auth patterns, adapted for South African stokvel regulations:
- Banks Act Exemption Notice 620 (2014)
- FICA (Financial Intelligence Centre Act) KYC requirements
- NASASA (National Stokvel Association of South Africa) guidelines

Key Features:
- OTP-based authentication (phone/email)
- JWT session management
- Role-based access control (Chairperson, Secretary, Treasurer, Member)
- SA ID number validation (Luhn algorithm)
- KYC/FICA document verification
- Multi-tenant organization isolation
"""

__version__ = "0.1.0"
