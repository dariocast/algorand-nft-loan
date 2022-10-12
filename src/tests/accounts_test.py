from beaker import sandbox

from src.utils.accounts import *
from src.utils.client import *


def internal_accounts():
    private_key, my_address = get_default_algorand_keypair()
    algod_client = get_algod_client(private_key, my_address)
    account_info = check_balance(algod_client, my_address)

def sandbox_accounts():
    # get accounts from sandbox
    accts = sandbox.get_accounts()
    # print accts info
    print(*accts, sep="\n", end="\n\n")
    index = 0
    for acct in accts:
        print(f"Account {index}:")
        print(f"Address: {acct.address}")
        print(f"Private key: {acct.private_key}")
        print(f"Signer: {acct.signer}")
        info = sandbox.get_algod_client().account_info(acct.address)
        print(f"Balance is {info.get('amount')}\n")
        index += 1


if __name__ == "__main__":
    sandbox_accounts()
