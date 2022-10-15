# Helper function to wait for a specific round
def wait_for_round(client, round_to_wait_for):
    last_round = client.status().get('last-round')
    print(f"Waiting for round {round_to_wait_for}")
    while last_round < round_to_wait_for:
        last_round += 1
        client.status_after_block(last_round)
        print(f"Round {last_round}")