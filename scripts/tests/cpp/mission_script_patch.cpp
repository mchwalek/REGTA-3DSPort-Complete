// Harness for test_mission_script_patch.py: PatchCalmBeforeTheStormSkip from
// stories/src/control/Script5.cpp is pasted in at FUNCTION. Reads argv[1],
// patches it in place, writes argv[2] and prints 1 if patched, 0 if not.
#include <cstdio>
#include <cstring>
#include <vector>
typedef unsigned char uint8;
typedef unsigned int uint32;

/*@FUNCTION@*/

int main(int argc, char **argv) {
	if (argc != 3)
		return 2;
	FILE *in = fopen(argv[1], "rb");
	if (!in)
		return 3;
	std::vector<uint8> data;
	int c;
	while ((c = fgetc(in)) != EOF)
		data.push_back((uint8)c);
	fclose(in);
	bool patched = PatchCalmBeforeTheStormSkip(data.data(), (uint32)data.size());
	FILE *out = fopen(argv[2], "wb");
	if (!out)
		return 4;
	fwrite(data.data(), 1, data.size(), out);
	fclose(out);
	printf("%d\n", patched ? 1 : 0);
	return 0;
}
