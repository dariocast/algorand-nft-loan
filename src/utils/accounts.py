from algosdk import account, mnemonic

default_account_passphrase = "plunge odor company index ceiling body frozen canvas soul tooth mule glass tip economy govern boost earth behind space gap galaxy myth alone ability access"
default_account_private_key = "N00mXSx3kmO0qyF9NrkiL0bxGKGsGSsihaD1dS9K3iD/TzTAL0NHyLofKOmq5tO+KtgQPQeeAwQjD7bxESsCmw=="
default_account_address = "75HTJQBPIND4ROQ7FDU2VZWTXYVNQEB5A6PAGBBDB63PCEJLAKNTZRVS3A"


# helper method to generate new algorand keypair
def generate_algorand_keypair():
    private_key, address = account.generate_account()
    print("My address: {}".format(address))
    print("My private key: {}".format(private_key))
    print("My passphrase: {}".format(mnemonic.from_private_key(private_key)))
    return private_key, address


# helper method to get previously generated and already funded algorand keypair
def get_default_algorand_keypair():
    private_key = default_account_private_key
    address = default_account_address
    return private_key, address


def check_balance(algod_client, my_address):
    account_info = algod_client.account_info(my_address)
    print("Account balance: {} microAlgos".format(account_info.get('amount')) + "\n")
    return account_info


def main():
    pass


if __name__ == "__main__":
    main()
