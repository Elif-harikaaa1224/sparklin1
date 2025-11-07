#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Protobuf encoding for Spark addresses
Based on Spark SDK address.ts implementation
"""

def encode_spark_address_protobuf(identity_public_key: bytes) -> bytes:
    """
    Encode a Spark address using protobuf format
    
    Protobuf structure:
    message SparkAddress {
      bytes identity_public_key = 1;  // tag 10 (field 1, wire type 2)
      SparkInvoiceFields spark_invoice_fields = 2;  // optional
      bytes signature = 3;  // optional
    }
    
    For a simple address (no invoice, no signature):
    - tag = 10 (field 1, wire type 2 = length-delimited)
    - length = 33 (compressed public key size)
    - data = 33 bytes of public key
    """
    if len(identity_public_key) != 33:
        raise ValueError(f"Public key must be 33 bytes, got {len(identity_public_key)}")
    
    # Protobuf encoding for field 1 (identity_public_key)
    # wire type 2 (length-delimited) = field_number << 3 | 2
    # field 1 << 3 | 2 = 8 | 2 = 10 = 0x0A
    tag = 10  # field 1, wire type 2
    length = len(identity_public_key)  # 33
    
    # Encode as: tag + length + data
    result = bytes([tag, length]) + identity_public_key
    
    return result
