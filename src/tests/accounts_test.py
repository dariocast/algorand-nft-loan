from src.utils.accounts import *
from src.utils.client import *


def main():
    private_key, my_address = get_default_algorand_keypair()
    algod_client = get_algod_client(private_key, my_address)
    account_info = check_balance(algod_client, my_address)


if __name__ == "__main__":
    main()
