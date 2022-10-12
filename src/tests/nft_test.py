from src.nft import create_default_nft
from src.utils.accounts import get_default_algorand_keypair
from src.utils.client import get_algod_client

nft_metadata_github_url = "https://raw.githubusercontent.com/dariocast/algorand-nft-loan/main/assets/nft_metadata.json"


def main():
    private_key, my_address = get_default_algorand_keypair()
    algod_client = get_algod_client(private_key, my_address)
    asset_id = create_default_nft(algod_client, private_key, my_address, "G3 NFT@arc3", "G3", nft_metadata_github_url)
    print("Created NFT with asset ID: {}".format(asset_id))


if __name__ == "__main__":
    main()
