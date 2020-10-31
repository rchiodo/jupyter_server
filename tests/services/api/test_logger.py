async def test_logger(fetch, ws_fetch, http_port, auth_header):
    print('hello')
    # Create logger
    r = await fetch(
        'api', 'logger',
        method='POST',
    )
    loggerid = json.loads(r.body.decode())['id']

    # Get kernel info
    r = await fetch(
        'api', 'kernels', kid,
        method='GET'
    )
    model = json.loads(r.body.decode())
    assert model['connections'] == 0

    time.sleep(1)
    # Open a websocket connection.
    ws = await ws_fetch(
        'api', 'kernels', kid, 'channels'
    )

    # Test that it was opened.
    r = await fetch(
        'api', 'kernels', kid,
        method='GET'
    )
    model = json.loads(r.body.decode())
    assert model['connections'] == 1

    # Close websocket
    ws.close()
    # give it some time to close on the other side:
    for i in range(10):
        r = await fetch(
            'api', 'kernels', kid,
            method='GET'
        )
        model = json.loads(r.body.decode())
        if model['connections'] > 0:
            time.sleep(0.1)
        else:
            break

    r = await fetch(
        'api', 'kernels', kid,
        method='GET'
    )
    model = json.loads(r.body.decode())
    assert model['connections'] == 0