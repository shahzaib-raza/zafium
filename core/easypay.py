import base64

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
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

    value = "&".join(
        f"{key}={value}"
        for key, value in sorted_fields
    )

    print(
        f"========== EASYPAISA HASH DEBUG ==========\n"
        f"{value}\n"
        f"=========================================="
    )

    key = settings.EASYPAY_HASH_KEY.encode("utf-8")

    cipher = AES.new(
        key,
        AES.MODE_ECB,
    )

    encrypted = cipher.encrypt(
        pad(
            value.encode("utf-8"),
            AES.block_size,
        )
    )

    return base64.b64encode(
        encrypted
    ).decode("utf-8")