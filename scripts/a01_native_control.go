// Local synthetic control only. No model endpoint, runtime or system changes.
package main

import (
	"bufio"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"sync"
)

func main() {
	listener, err := net.ListenTCP("tcp4", &net.TCPAddr{IP: net.IPv4(127, 0, 0, 1)})
	if err != nil {
		panic(err)
	}
	encoder := json.NewEncoder(os.Stdout)
	encoder.Encode(map[string]any{"port": listener.Addr().(*net.TCPAddr).Port})
	var worker sync.WaitGroup
	var events []map[string]any
	worker.Add(1)
	go func() {
		defer worker.Done()
		conn, err := listener.AcceptTCP()
		if err != nil {
			return
		}
		defer conn.Close()
		// Match Python's default server control; do not select a production option.
		if err := conn.SetNoDelay(false); err != nil {
			panic(err)
		}
		request, err := http.ReadRequest(bufio.NewReader(conn))
		if err != nil {
			panic(err)
		}
		raw, err := io.ReadAll(request.Body)
		if err != nil {
			panic(err)
		}
		request.Body.Close()
		sum := sha256.Sum256(raw)
		events = append(events, map[string]any{"event": "request", "bytes": len(raw), "sha256": hex.EncodeToString(sum[:])})
		body := append(append(bytes.Repeat([]byte(`{"x":`), 4000), '0'), bytes.Repeat([]byte("}"), 4000)...)
		_, err = fmt.Fprintf(conn, "HTTP/1.0 200 OK\r\nContent-Length: %d\r\n\r\n", len(body))
		if err != nil {
			panic(err)
		}
		count, err := conn.Write(body)
		event := map[string]any{"event": "write_returned", "bytes": count, "tcp_nodelay": false}
		if err != nil {
			event["error"] = err.Error()
		}
		events = append(events, event)
	}()
	bufio.NewReader(os.Stdin).ReadString('\n')
	listener.Close()
	worker.Wait()
	encoder.Encode(map[string]any{"events": events})
}
