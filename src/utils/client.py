import os

from algosdk.v2client import algod

from src.utils.accounts import generate_algorand_keypair


def get_algod_client(private_key, my_address):
    # set the address and token from the environment variables, otherwise use the sandbox values
    algod_address = os.environ.get("ALGOD_ADDRESS","http://localhost:4001")
    algod_token = os.environ.get("ALGOD_TOKEN","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    headers = {
        "X-API-Key": algod_token,
    }
    algod_client = algod.AlgodClient(algod_token, algod_address, headers)
    return algod_client