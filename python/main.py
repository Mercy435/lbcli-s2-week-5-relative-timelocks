from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

def main():

    try:
        # Connect to Bitcoin Core RPC with basic credentials
        rpc_user = "alice"
        rpc_password ="password"
        rpc_host = "127.0.0.1"
        rpc_port = 18443
        base_rpc_url = f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}"

        # General client for non-wallet-specific commands
        client = AuthServiceProxy(base_rpc_url)

        # Get blockchain info
        blockchain_info = client.getblockchaininfo()
        print("Blockchain Info:", blockchain_info)

        #1.  Create two wallets called Miner and Alice
        # logic to optionally create/load them if they do not exist or are not loaded already.
        def get_wallet_rpc(base_url, wallet_name):
            """
            Return an AuthServiceProxy instance scoped to the given wallet.
            """
            wallet_url = f"{base_url}/wallet/{wallet_name}"
            return AuthServiceProxy(wallet_url)
        
        def load_or_create_wallet(client, base_url, wallet_name):                               
            """
            Load the wallet if it exists and is loaded.
            If exists but not loaded, load it.
            If does not exist, create and load it.
            Returns a wallet-specific AuthServiceProxy client.
            """
            wallets_on_disk = [w['name'] for w in client.listwalletdir()['wallets']]
            wallets_loaded = client.listwallets()

            if wallet_name not in wallets_on_disk:
                client.createwallet(wallet_name)
            elif wallet_name not in wallets_loaded:
                client.loadwallet(wallet_name)

            return get_wallet_rpc(base_url, wallet_name)
        
        # Create/Load the wallets called Miner and Alice
        miner_wallet = load_or_create_wallet(client, base_rpc_url, "Miner")
        alice_wallet = load_or_create_wallet(client, base_rpc_url, "Alice")
        
        #2. Fund the Miner wallet
        blocks_to_mine = 101
        miner_address = miner_wallet.getnewaddress()
        miner_wallet.generatetoaddress(blocks_to_mine, miner_address) 
        
        #3. Send some coins to Alice's wallet
        # generate  new address for alice to receive some coin from miner say 30btc
        alice_address = alice_wallet.getnewaddress()
        miner_wallet.sendtoaddress(alice_address, 30) 
        # mine one block to confirm transaction for it to reflect in alice balance
        miner_wallet.generatetoaddress(1, miner_address)
        #check alice balance
        alice_balance =alice_wallet.getbalance()
        
        #4. Create refund transaction where Alice pays 10 BTC to Miner
        # Additionally, add a relative timelock of 10 blocks
        # Create relative timelock redeem script
        #get miner puband private key
        miner_addr = miner_wallet.getnewaddress()
        spendable_utxo = alice_wallet.listunspent()[0]  
        inputs = [{
            "txid": spendable_utxo["txid"],
            "vout": spendable_utxo["vout"],
            "sequence": 10
        }]
        #generate change address for alice
        alice_change_address = alice_wallet.getrawchangeaddress()
        outputs= {
            miner_addr: 10,
            alice_change_address:19.99999  # Implies fee of  0.00001000 BTC
        }
        #relative timelock transaction
        relative_timelock_transaction = alice_wallet.createrawtransaction(inputs, outputs)  

        #5.  Sign and broadcast the transaction. Is the broadcast successful? 
        signed_tx = alice_wallet.signrawtransactionwithwallet(relative_timelock_transaction)
        try:
            txid = alice_wallet.sendrawtransaction(signed_tx["hex"])
        except Exception as e:
            print(f"wait 10 more blocks to broadcast- {e}")

       # No, it was not  successful; an error message "-Error occurred: -26: non-BIP68-final" was returned
       #This comes from BIP 68, which defines relative timelocks based on the nSequence field. Bitcoin Core rejects transactions from entering the mempool if they spend an input with a relative timelock that hasn’t passed yet.

        # 6.  Generate 10 blocks
        miner_wallet.generatetoaddress(10, miner_address)

        # 7. Broadcast the transaction again. Is the broadcast successful now?  
        spend_txid = miner_wallet.sendrawtransaction(signed_tx["hex"])
        # mine one block to confirm transaction for it to reflect in alice balance
        miner_wallet.generatetoaddress(1, miner_address)
                
        # 8.  Check Alice's final balance
        print("Alice Final Balance:", alice_wallet.getbalance())  
        
        # 9. Output the transaction ID to `out.txt`
        with open("out.txt", "w") as f:
                f.write(f"{spend_txid}\n")
        
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()