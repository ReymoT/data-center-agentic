// Synthetic exact-wire control only. No model endpoint or shared configuration.
package main

import (
	"bufio"
	"bytes"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"os"
	"sync"
	"time"
)

func digest(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func main() {
	input := bufio.NewReader(os.Stdin)
	line, err := input.ReadBytes('\n')
	if err != nil {
		panic(err)
	}
	var config struct {
		Wire string `json:"wire_base64"`
		Mode string `json:"close_mode"`
	}
	if err := json.Unmarshal(line, &config); err != nil {
		panic(err)
	}
	wire, err := base64.StdEncoding.DecodeString(config.Wire)
	if err != nil {
		panic(err)
	}
	boundary := bytes.Index(wire, []byte("\r\n\r\n")) + 4
	if boundary < 4 || (config.Mode != "original_close" && config.Mode != "wait_for_client") {
		panic("invalid synthetic configuration")
	}
	listener, err := net.ListenTCP("tcp4", &net.TCPAddr{IP: net.IPv4(127, 0, 0, 1)})
	if err != nil {
		panic(err)
	}
	encoder := json.NewEncoder(os.Stdout)
	encoder.Encode(map[string]any{"port": listener.Addr().(*net.TCPAddr).Port})
	result := map[string]any{"configured_wire_sha256": digest(wire), "close_mode": config.Mode}
	var worker sync.WaitGroup
	worker.Add(1)
	go func() {
		defer worker.Done()
		conn, err := listener.AcceptTCP()
		if err != nil {
			result["accept_error"] = err.Error()
			return
		}
		defer conn.Close()
		if err := conn.SetDeadline(time.Now().Add(12 * time.Second)); err != nil {
			panic(err)
		}
		if err := conn.SetNoDelay(false); err != nil {
			panic(err)
		}
		request, err := http.ReadRequest(bufio.NewReader(conn))
		if err != nil {
			result["read_error"] = err.Error()
			return
		}
		body, err := io.ReadAll(request.Body)
		request.Body.Close()
		if err != nil {
			result["body_error"] = err.Error()
			return
		}
		result["request_bytes"], result["request_sha256"] = len(body), digest(body)
		// Preserve captured header/body bytes and the Python fixture's two writes.
		nh, err := conn.Write(wire[:boundary])
		result["header_write_bytes"] = nh
		if err != nil {
			result["header_write_error"] = err.Error()
			return
		}
		nb, err := conn.Write(wire[boundary:])
		result["body_write_bytes"] = nb
		if err != nil {
			result["body_write_error"] = err.Error()
			return
		}
		if config.Mode == "wait_for_client" {
			var tail [1]byte
			n, err := conn.Read(tail[:])
			result["client_eof"] = err == io.EOF
			result["extra_request_bytes"] = n
			if err != nil && err != io.EOF {
				result["wait_error"] = err.Error()
			}
		}
	}()
	input.ReadBytes('\n')
	listener.Close()
	worker.Wait()
	encoder.Encode(result)
}
