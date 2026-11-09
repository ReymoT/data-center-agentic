// Offline A01 grammar probe. Ollama 0.40.5 (tag commit d919272e) converts a request
// "format" schema with its bundled llama-server, built from llama.cpp b11669 (commit
// 620d2225). This program calls the same json_schema_to_grammar function and checks
// synthetic strings against the compiled grammar. No model, runtime or network use.
// Build it against a llama.cpp b11669 build tree; see
// docs/handoffs/A01_CLAIM_VALUE_UNIT_PAIRING_2026-11-09.md.
// usage: grammar_probe SCHEMA.json CASES.tsv GRAMMAR_OUT.gbnf
// CASES.tsv: one case per line, "name<TAB>text"; prints "name<TAB>ACCEPT|REJECT".
#include "json-schema-to-grammar.h"
#include "../src/llama-grammar.h"
#include "../src/unicode.h"
#include "json.h"
#include <fstream>
#include <iostream>
#include <sstream>

static std::string slurp(const char * p) { std::ifstream f(p); std::stringstream s; s << f.rdbuf(); return s.str(); }

static bool match_string(const std::string & input, llama_grammar * grammar) {
    auto & stacks = llama_grammar_get_stacks(grammar);
    size_t offset = 0;
    while (offset < input.size()) {
        uint32_t cpt = unicode_cpt_from_utf8(input, offset);
        try { llama_grammar_accept_token(*grammar, 0, unicode_cpt_to_utf8(cpt)); }
        catch (const std::runtime_error &) { return false; }
        if (stacks.empty()) return false;
    }
    for (const auto & st : stacks) if (st.empty()) return true;
    return false;
}

int main(int argc, char ** argv) {
    if (argc != 4) { std::cerr << "usage: grammar_probe SCHEMA CASES GRAMMAR_OUT\n"; return 2; }
    std::string gbnf;
    try { gbnf = json_schema_to_grammar(common_json::parse(slurp(argv[1]))); }
    catch (const std::exception & e) { std::cout << "CONVERSION_ERROR\t" << e.what() << "\n"; return 1; }
    std::ofstream(argv[3]) << gbnf;
    llama_grammar * g = llama_grammar_init_impl(nullptr, gbnf.c_str(), "root", false, nullptr, 0, nullptr, 0);
    if (!g) { std::cout << "GRAMMAR_BUILD_FAILED\n"; return 1; }
    const auto original = llama_grammar_get_stacks(g);
    std::ifstream cf(argv[2]); std::string line;
    while (std::getline(cf, line)) {
        if (line.empty()) continue;
        auto tab = line.find('\t');
        llama_grammar_get_stacks(g) = original;
        std::cout << line.substr(0, tab) << "\t" << (match_string(line.substr(tab + 1), g) ? "ACCEPT" : "REJECT") << "\n";
    }
    llama_grammar_free_impl(g);
    return 0;
}
