from mnemonic import Mnemonic
import secrets
from pycoin.key.BIP32Node import BIP32Node

def test():
    m = Mnemonic('english')

    #mnemonic_seed = m.to_mnemonic(secrets.token_bytes(256 // 8))

    # Test account:
    # Test user 1
    #root_seeds = {
    #    'mnemonic': 'text satoshi giant carbon bamboo cute utility matrix fee royal apology like swim brother tuition rocket lift hen ozone machine shop catch apology tourist',
    #    'salt': 'nl0pFAv5mwIAcgPyfgks6hGRmnd1PQKDSfP77twc9Hq6XxTqwdQstali4T-cPZ-K',
    #}
    # Test user 2
    #root_seeds = {
    #    'mnemonic': 'net veteran ketchup original deliver weasel afford world protect retreat leader embody replace install course push duty biology rule wink rule diamond pelican rib',
    #    'salt': 'nl0pFAv5mwIAcgPyfgks6hGRmnd1PQKDSfP77twc9Hq6XxTqwdQstali4T-cPZ-K',
    #}
    # Test user 3
    root_seeds = {
        'mnemonic': 'file coyote vessel improve excuse human shrimp nation ridge blast cash original ginger exchange dish situate during blush chief equal buyer matter visual ritual',
        'salt': 'nl0pFAv5mwIAcgPyfgks6hGRmnd1PQKDSfP77twc9Hq6XxTqwdQstali4T-cPZ-K',
    }
    # dev.net account:
    #root_seeds = {
    #    'mnemonic': 'holiday direct again wage any bleak dawn document lucky lizard become adjust rug metal patch coin warm future exhibit giggle treat stadium cruel soup',
    #    'salt': 'nyLIvi4XMkoUC_0_Gex9MiJsXMH5iI8xzMZ1qQPZk97QmZIiR-UPjw-XxjW2Xng3',
    #}
    print("root_seeds: %s" % root_seeds)
    salted_mnemonic = m.to_seed(root_seeds['mnemonic'], passphrase=root_seeds['salt'])
    #root_wallet = BIP32Node.from_master_secret(master_secret=salted_mnemonic, netcode='XTN')
    root_wallet = BIP32Node.from_master_secret(master_secret=salted_mnemonic, netcode='XLT')
    #root_wallet = BIP32Node.from_master_secret(master_secret=salted_mnemonic, netcode='XDT')
    # https://github.com/satoshilabs/slips/blob/master/slip-0044.md
    path = [
        "44H",  # purpose (bip44)
        "1H",   # testnet
        #"0H",   # bitcoin (XTN)
        "2H",   # litecoin (XLT)
        #"3H",   # dogecoin (XDT)
    ]
    coin_account_key = root_wallet.subkey_for_path("/".join(path))
    coin_account_private_key = coin_account_key.wallet_key(as_private=True)
    coin_account_public_key = coin_account_key.wallet_key(as_private=False)
    print("-----");
    print("base coin_account_key: %s" % coin_account_key)

    #print("override to match dev")
    #coin_account_private_key = 'ttpv9DMsjBtT2QWNej4AMNfVqnMS1nAcyDty7yMEsqJdbPkcMC5XM8JEkGj52hboe8ThCHS7gMPgZHTwRegeautHywedUgcXYfoAfMTE1fpgDKk'
    #coin_account_public_key = 'ttub4eYDKyJzGZ3LGbkzbz9svNBeTLrp3UTdCVTGYp4vXaYCwZGbg3LfksqLH58si5gAkCa8Yu4bff7m3FyQvRiu4NdDsLnwhvaGzbHSaVom6Bd'

    print("base coin_account_key public: %s" % coin_account_public_key)
    print("base coin_account_key private: %s" % coin_account_private_key)
    print("-----");

    '''
    Private key (from database):
    ttpv9DMsjBtT2QWNej4AMNfVqnMS1nAcyDty7yMEsqJdbPkcMC5XM8JEkGj52hboe8ThCHS7gMPgZHTwRegeautHywedUgcXYfoAfMTE1fpgDKk
    ttub4eYDKyJzGZ3LGbkzbz9svNBeTLrp3UTdCVTGYp4vXaYCwZGbg3LfksqLH58si5gAkCa8Yu4bff7m3FyQvRiu4NdDsLnwhvaGzbHSaVom6Bd
    '''

    print("deriving 20 addresses:")
    for index in range(0, 20):
        coin_wallet = BIP32Node.from_hwif(coin_account_private_key)
        subkey = coin_wallet.subkey_for_path("0/%d" % index)
        #print("  address %d: %s" % (index, subkey.bitcoin_address()))
        #print("   wif: %s" % subkey.wif())
        print("'%s'," % subkey.bitcoin_address())

    '''
    print("deriving 20 change addresses:")
    for index in range(0, 20):
        coin_wallet = BIP32Node.from_hwif(coin_account_private_key)
        subkey = coin_wallet.subkey_for_path("1/%d" % index)
        #print("  address %d: %s" % (index, subkey.bitcoin_address()))
        #print("   wif: %s" % subkey.wif())
        print("'%s'," % subkey.bitcoin_address())

    #subkey = coin_wallet.subkey(i=0)
    #subsubkey = subkey.subkey(i=0)
    #print("address: %s" % subsubkey.bitcoin_address())
    #print("wif: %s" % subsubkey.wif())
    #print("-----");
    '''


if __name__ == '__main__':
    test()
