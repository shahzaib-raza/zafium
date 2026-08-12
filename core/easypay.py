import base64

from Crypto.Cipher import AES
from django.conf import settings


def generate_easypay_hash(fields):
    """
    Generate merchantHashedReq according to
    Easypaisa Merchant Integration Guide.

    Algorithm:
        1. Sort field names alphabetically
        2. Build key=value pairs joined by &
        3. AES/ECB/PKCS5Padding
        4. Base64 encode
    """

    # Easypaisa requires alphabetical ordering
    sorted_fields = sorted(fields.items())

    # Build:
    # amount=10.0&autoRedirect=0&expiryDate=...
    value = "&".join(
        f"{key}={value}"
        for key, value in sorted_fields
    )

    # Easypaisa hash key
    key = settings.EASYPAY_HASH_KEY.encode("utf-8")

    # AES uses 16-byte blocks
    data = value.encode("utf-8")

    # PKCS5/PKCS7 padding
    padding_length = 16 - (len(data) % 16)

    padded_data = data + bytes(
        [padding_length] * padding_length
    )

    cipher = AES.new(
        key,
        AES.MODE_ECB,
    )

    encrypted = cipher.encrypt(padded_data)

    return base64.b64encode(
        encrypted
    ).decode("utf-8")