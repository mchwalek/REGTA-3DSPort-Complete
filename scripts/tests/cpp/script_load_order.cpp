// Harness for test_script_load_order.py: SortScriptListByCreationOrder from
// stories/src/control/Script5.cpp is pasted in at FUNCTION; each test supplies
// its own main() body (generated from its id list) at MAIN_BODY.
#include <cassert>
#include <cstdio>
typedef int int32;
#define nil 0
struct CRunningScript {
	CRunningScript *next;
	CRunningScript *prev;
	int32 m_nId;
};

/*@FUNCTION@*/

static CRunningScript *build(int32 *ids, int n) {
	CRunningScript *nodes = new CRunningScript[n];
	for (int i = 0; i < n; i++) {
		nodes[i].m_nId = ids[i];
		nodes[i].next = (i + 1 < n) ? &nodes[i + 1] : (CRunningScript*)nil;
		nodes[i].prev = (i > 0) ? &nodes[i - 1] : (CRunningScript*)nil;
	}
	return n > 0 ? nodes : (CRunningScript*)nil;
}

static void check_consistent(CRunningScript *list) {
	CRunningScript *prev = (CRunningScript*)nil;
	while (list != nil) {
		assert(list->prev == prev);
		prev = list;
		list = list->next;
	}
}

static void expect_ids(CRunningScript *list, int32 *expected, int n) {
	for (int i = 0; i < n; i++) {
		assert(list != nil);
		assert(list->m_nId == expected[i]);
		list = list->next;
	}
	assert(list == nil);
}

int main() {
/*@MAIN_BODY@*/
}
