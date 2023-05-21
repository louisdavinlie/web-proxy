To compile and run the proxy:
1. run `python3 proxy.py {PORT} {IMAGE-FLAG} {ATTACK-FLAG}` where:
    - `PORT` is the port number the proxy is listening on
    - `IMAGE-FLAG` is a binary value to specify if the proxy applies image substitution (0 for no substitution, 1 for substitution)
    - `ATTACK-FLAG` is a binary value to specify if the proxy is implementing an attacker mode (0 for no attack, 1 for attack)
2. The first line printed will be `Server started on port {PORT}.` upon successful run