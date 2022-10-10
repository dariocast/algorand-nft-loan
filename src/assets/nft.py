import json
from hashlib import sha256

from algosdk.future.transaction import AssetConfigTxn, wait_for_confirmation

default_nft_id = 0


def create_default_nft(client, private_key, address, asset_name, asset_unit_name, asset_url):
    # create a new asset
    # note that the manager, reserve, freeze, and clawback
    # are all empty for the nft as specified in documentation
    # https://developer.algorand.org/docs/get-started/tokenization/nft/

    f = open('../../assets/nft_metadata.json')
    json_metadata = json.load(f)
    f.close()

    asset_metadata_hash = sha256(json.dumps(json_metadata).encode('utf-8')).digest()

    print("Creating transaction...")
    txn = AssetConfigTxn(
        sender=address,
        sp=client.suggested_params(),
        total=1,
        decimals=0,
        default_frozen=False,
        unit_name=asset_unit_name,
        asset_name=asset_name,
        url=asset_url,
        metadata_hash=asset_metadata_hash,
        note=b"NFT creation",
        strict_empty_address_check=False,
        manager="",
        reserve="",
        freeze="",
        clawback="",
    )

    # sign the transaction
    print("Signing transaction...")
    signed_txn = txn.sign(private_key)

    # send the transaction to the network and retrieve the txid
    print("Sending transaction...")
    txid = client.send_transaction(signed_txn)

    # wait for confirmation
    print("Waiting for confirmation...")
    wait_for_confirmation(algod_client=client, txid=txid)

    # retrieve the asset id of the newly created asset
    ptx = client.pending_transaction_info(txid)
    asset_id = ptx["asset-index"]
    print("Created NFT with asset ID: {}".format(asset_id))

    return asset_id


# Just as a reference, this is the json metadata that is used in ARC-003
# https://arc.algorand.foundation/ARCs/arc-0003#json-metadata-file-schema
json_metadata_template = {
    "title": "Token Metadata",
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Identifies the asset to which this token represents"
        },
        "decimals": {
            "type": "integer",
            "description": "The number of decimal places that the token amount should display - e.g. 18, means to divide the token amount by 1000000000000000000 to get its user representation."
        },
        "description": {
            "type": "string",
            "description": "Describes the asset to which this token represents"
        },
        "image": {
            "type": "string",
            "description": "A URI pointing to a file with MIME type image/* representing the asset to which this token represents. Consider making any images at a width between 320 and 1080 pixels and aspect ratio between 1.91:1 and 4:5 inclusive."
        },
        "image_integrity": {
            "type": "string",
            "description": "The SHA-256 digest of the file pointed by the URI image. The field value is a single SHA-256 integrity metadata as defined in the W3C subresource integrity specification (https://w3c.github.io/webappsec-subresource-integrity)."
        },
        "image_mimetype": {
            "type": "string",
            "description": "The MIME type of the file pointed by the URI image. MUST be of the form 'image/*'."
        },
        "background_color": {
            "type": "string",
            "description": "Background color do display the asset. MUST be a six-character hexadecimal without a pre-pended #."
        },
        "external_url": {
            "type": "string",
            "description": "A URI pointing to an external website presenting the asset."
        },
        "external_url_integrity": {
            "type": "string",
            "description": "The SHA-256 digest of the file pointed by the URI external_url. The field value is a single SHA-256 integrity metadata as defined in the W3C subresource integrity specification (https://w3c.github.io/webappsec-subresource-integrity)."
        },
        "external_url_mimetype": {
            "type": "string",
            "description": "The MIME type of the file pointed by the URI external_url. It is expected to be 'text/html' in almost all cases."
        },
        "animation_url": {
            "type": "string",
            "description": "A URI pointing to a multi-media file representing the asset."
        },
        "animation_url_integrity": {
            "type": "string",
            "description": "The SHA-256 digest of the file pointed by the URI external_url. The field value is a single SHA-256 integrity metadata as defined in the W3C subresource integrity specification (https://w3c.github.io/webappsec-subresource-integrity)."
        },
        "animation_url_mimetype": {
            "type": "string",
            "description": "The MIME type of the file pointed by the URI animation_url. If the MIME type is not specified, clients MAY guess the MIME type from the file extension or MAY decide not to display the asset at all. It is STRONGLY RECOMMENDED to include the MIME type."
        },
        "properties": {
            "type": "object",
            "description": "Arbitrary properties (also called attributes). Values may be strings, numbers, object or arrays."
        },
        "extra_metadata": {
            "type": "string",
            "description": "Extra metadata in base64. If the field is specified (even if it is an empty string) the asset metadata (am) of the ASA is computed differently than if it is not specified."
        },
        "localization": {
            "type": "object",
            "required": ["uri", "default", "locales"],
            "properties": {
                "uri": {
                    "type": "string",
                    "description": "The URI pattern to fetch localized data from. This URI should contain the substring `{locale}` which will be replaced with the appropriate locale value before sending the request."
                },
                "default": {
                    "type": "string",
                    "description": "The locale of the default data within the base JSON"
                },
                "locales": {
                    "type": "array",
                    "description": "The list of locales for which data is available. These locales should conform to those defined in the Unicode Common Locale Data Repository (http://cldr.unicode.org/)."
                },
                "integrity": {
                    "type": "object",
                    "patternProperties": {
                        ".*": {"type": "string"}
                    },
                    "description": "The SHA-256 digests of the localized JSON files (except the default one). The field name is the locale. The field value is a single SHA-256 integrity metadata as defined in the W3C subresource integrity specification (https://w3c.github.io/webappsec-subresource-integrity)."
                }
            }
        }
    }
}
