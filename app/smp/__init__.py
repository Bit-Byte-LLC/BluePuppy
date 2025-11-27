"""SMP protocol package initialization."""

from .cbor_codec import CBORError, decode, encode, validate_response
from .client import SMPClient, SMPTransport
from .fs_mgmt import (
    FsMgmtCommand,
    build_hash_request,
    build_stat_request,
    parse_hash_response,
    parse_stat_response,
)
from .img_mgmt import (
    ImageSlot,
    ImgMgmtCommand,
    ImgMgmtError,
    build_erase_request,
    build_list_request,
    build_test_request,
    build_upload_request,
    parse_erase_response,
    parse_list_response,
    parse_test_response,
    parse_upload_response,
)
from .pdu import (
    SMP_HEADER_SIZE,
    SMPError,
    SMPGroup,
    SMPHeader,
    SMPOp,
    SMPPDU,
    create_request,
    validate_response as validate_pdu_response,
)

__all__ = [
    # cbor_codec
    "CBORError",
    "decode",
    "encode",
    "validate_response",
    # client
    "SMPClient",
    "SMPTransport",
    # fs_mgmt
    "FsMgmtCommand",
    "build_hash_request",
    "build_stat_request",
    "parse_hash_response",
    "parse_stat_response",
    # img_mgmt
    "ImageSlot",
    "ImgMgmtCommand",
    "ImgMgmtError",
    "build_erase_request",
    "build_list_request",
    "build_test_request",
    "build_upload_request",
    "parse_erase_response",
    "parse_list_response",
    "parse_test_response",
    "parse_upload_response",
    # pdu
    "SMP_HEADER_SIZE",
    "SMPError",
    "SMPGroup",
    "SMPHeader",
    "SMPOp",
    "SMPPDU",
    "create_request",
    "validate_pdu_response",
]
