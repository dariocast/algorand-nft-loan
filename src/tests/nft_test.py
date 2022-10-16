from src import utils
from src.utils import create_default_nft

nft_metadata_github_url = "https://raw.githubusercontent.com/dariocast/algorand-nft-loan/main/assets/nft_metadata.json"


def main():
    my_private_key = utils.get_private_key_from_mnemonic(utils.mnemonics[0])
    my_address = utils.get_address_from_private_key(my_private_key)
    algod_client = utils.get_algod_client()
    asset_id = create_default_nft(algod_client, my_private_key, my_address, "G3 NFT@arc3", "G3", nft_metadata_github_url)
    print("Created NFT with asset ID: {}".format(asset_id))


if __name__ == "__main__":
    main()
