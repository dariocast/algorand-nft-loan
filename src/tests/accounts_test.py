from beaker import sandbox

from src import utils
from src.utils import mnemonics


def internal_accounts():
    my_private_key = utils.get_private_key_from_mnemonic(mnemonics[0])
    my_address = utils.get_address_from_private_key(my_private_key)
    algod_client = utils.get_algod_client()
    account_info = utils.check_balance(algod_client, my_address)


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
