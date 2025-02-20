# All functions for stat generation

###########
# Imports #
###########
from datetime import datetime

from db_funcs import get_tx_from_db_by_version, get_latest_version


#########
# Funcs #
#########
def days_hours_minutes_seconds(td):
    return td.days, td.seconds//3600, (td.seconds//60) % 60, (td.seconds % 60)


def calc_stats(c, limit = None):
    # time
    cur_time = datetime.now()

    # time expression
    if limit:
        n = int(cur_time.timestamp()) - limit
        # TODO: using heuristic of expiration_time - 100 = tx time until there is a better way
        # see: https://community.libra.org/t/fetch-previous-version-ledgerinfo-via-rpc/848/6
        t_str = ' and expiration_unixtime >= ' + str(n + 100) + ' and expiration_unixtime < 2147485547'
        # TODO: limiting the top of the counter means we're discounting TXs with high expriation time in stats - fix it
    else:
        t_str = ''

    # first block
    c.execute("SELECT MIN(version) FROM transactions WHERE version > 0" + t_str)
    first_version = c.fetchall()[0][0]
    first_block_time = datetime.fromtimestamp(get_tx_from_db_by_version(first_version, c)[10])

    # get max block
    last_block = get_latest_version(c)
    print('last block = ', last_block)

    # deltas
    td = cur_time - first_block_time
    dhms = days_hours_minutes_seconds(td)
    blocks_delta = last_block - first_version + 1

    # mints
    c.execute("SELECT count(DISTINCT version) FROM transactions WHERE type = 'mint_transaction'" + t_str)
    mint_count = c.fetchall()[0][0]
    c.execute("SELECT DISTINCT version FROM transactions WHERE type = 'mint_transaction'" + t_str)
    mint_sum = sum([x[0] for x in c.fetchall()])

    # p2p txs
    c.execute("SELECT count(DISTINCT version) FROM transactions WHERE type = 'peer_to_peer_transaction'" + t_str)
    p2p_count = c.fetchall()[0][0]
    c.execute("SELECT DISTINCT version FROM transactions WHERE type = 'peer_to_peer_transaction'" + t_str)
    p2p_sum = sum([x[0] for x in c.fetchall()])

    # add 1 to account for the genesis block until it is added to DB
    c.execute("SELECT count(DISTINCT version) FROM transactions " +
              "WHERE (type != 'peer_to_peer_transaction') and (type != 'mint_transaction')" + t_str)
    other_tx_count = c.fetchall()[0][0]
    if limit is None:
        other_tx_count += 1  # TODO: this is for genesis block - remove later
    c.execute("SELECT DISTINCT version FROM transactions " +
              "WHERE (type != 'peer_to_peer_transaction') and (type != 'mint_transaction')" + t_str)
    other_sum = sum([x[0] for x in c.fetchall()])

    print('p2p + mint =', mint_count + p2p_count)

    # unique accounts
    c.execute("SELECT COUNT(DISTINCT dest) FROM transactions WHERE version > 0" + t_str)
    count_dest = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT src) FROM transactions WHERE version > 0" + t_str)
    count_src = c.fetchone()[0]

    r = (blocks_delta, *dhms, blocks_delta/td.total_seconds(), 100*mint_count/blocks_delta,
         100*p2p_count/blocks_delta, 100*other_tx_count/blocks_delta, mint_sum, p2p_sum, other_sum,
         count_dest, count_src)
    return r
