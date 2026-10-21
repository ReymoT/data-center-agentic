// Offline research only: render the installed Go template for the two-message
// Q09 probe. This does not prove that a particular Ollama runtime uses this path.
// Uses Go's real template engine, with the restricted system/user inputs from
// Ollama v0.40.6 template.Values processing. No network or model execution.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"text/template"
)

type message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

func run() error {
	var input struct {
		Template string    `json:"template"`
		Messages []message `json:"messages"`
	}
	if err := json.NewDecoder(os.Stdin).Decode(&input); err != nil {
		return err
	}
	if len(input.Messages) != 2 || input.Messages[0].Role != "system" || input.Messages[1].Role != "user" {
		return fmt.Errorf("research renderer accepts exactly system then user")
	}
	parsed, err := template.New("q09").Option("missingkey=zero").Parse(input.Template)
	if err != nil {
		return err
	}
	var output bytes.Buffer
	err = parsed.Execute(&output, map[string]any{
		"System": input.Messages[0].Content, "Messages": input.Messages,
		"Tools": nil, "Think": false, "IsThinkSet": true,
	})
	if err != nil {
		return err
	}
	return json.NewEncoder(os.Stdout).Encode(map[string]string{"prompt": output.String()})
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
