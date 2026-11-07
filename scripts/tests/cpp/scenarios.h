// Run one named scenario per process: `./test <name>` prints "ok" on success.
//   int main(int argc, char **argv) { SCENARIOS_BEGIN SCENARIO(foo) SCENARIO(bar) SCENARIOS_END }
#pragma once
#include <cstdio>
#include <cstring>

#define SCENARIOS_BEGIN if (argc != 2) { fprintf(stderr, "usage: %s <scenario>\n", argv[0]); return 2; }
#define SCENARIO(name) if (strcmp(argv[1], #name) == 0) { name(); printf("ok\n"); return 0; }
#define SCENARIOS_END fprintf(stderr, "unknown scenario %s\n", argv[1]); return 2;
