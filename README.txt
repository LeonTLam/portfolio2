DISCLAIMER
	-i, -ip is by default h3's ip-address
	-p, -port is by default 24
	
	h1 will always be invoked as server (receiver)
	h3 will always be invoked as client (sender)

TASK 1
	stop-and-wait
		RTT 25ms, 50ms, 100ms
			python3 dtrp.py -s -f image.jpg -r saw
			python3 dtrp.py -c -f img.jpg -r saw
	go-back-n
		RTT 25ms, 50ms, 100ms
			python3 dtrp.py -s -f image.jpg -r gbn
			python3 dtrp.py -c -f img.jpg -r gbn -w 5,10,15
	go-back-n-sr
		RTT 25ms, 50ms, 100ms
			python3 dtrp.py -s -f image.jpg -r gbn-sr
			python3 dtrp.py -c -f img.jpg -r gbn-sr -w 5,10,15

TASK 2
	stop-and-wait, go-back-n, go-back-n-sr
		sudo python3 simple-topolgy.py --link tc
		mininet> net.configLinkStatus('h3', 'r2', 'loss 10%')

TASK 3
	stop-and-wait
		sudo python3 simple-topolgy.py --link tc
		mininet> net.configLinkStatus('h3', 'r2', 'loss 10%')

TASK 4
	stop-and-wait
		sudo python3 simple-topolgy.py --link tc
		mininet> net.configLinkStatus('h3', 'r2', 'loss 5%')
	go-back-n
		sudo python3 simple-topolgy.py --link tc
		mininet> net.configLinkStatus('h3', 'r2', 'loss 5%')