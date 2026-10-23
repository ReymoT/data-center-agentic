// Offline Go-template reference only. Not a runtime counter or inference path.
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
	decoder := json.NewDecoder(os.Stdin)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&input); err != nil {
		return err
	}
	if len(input.Messages) < 2 {
		return fmt.Errorf("system then user required")
	}
	values := make([]map[string]any, 0, len(input.Messages))
	for i, m := range input.Messages {
		expected := "user"
		if i == 0 {
			expected = "system"
		} else if i%2 == 0 {
			expected = "assistant"
		}
		if m.Role != expected || m.Content == "" {
			return fmt.Errorf("only alternating nonempty text histories")
		}
		values = append(values, map[string]any{"Role": m.Role, "Content": m.Content, "Thinking": "", "ToolCalls": nil})
	}
	parsed, err := template.New("q09-history").Option("missingkey=zero").Parse(input.Template)
	if err != nil {
		return err
	}
	var output bytes.Buffer
	err = parsed.Execute(&output, map[string]any{"System": input.Messages[0].Content, "Messages": values, "Tools": nil, "Think": false, "IsThinkSet": true})
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
