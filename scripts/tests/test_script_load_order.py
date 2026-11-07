#!/usr/bin/env python3
"""Regression test for the TR1 "Wong Side of the Tracks" mis-spawn bug.

SaveAllScripts walks pActiveScripts head->tail, but LoadAllScripts restores
each record through StartNewScript, which head-inserts -- so every save/load
round trip reverses script execution order, and the parity alternates on
each cycle. When the reversed parity puts TCHRM ahead of CARM in the same
frame, TCHRM latches a stale (zero) vehicle handle and TR1 launches with no
vehicle to teleport, silently leaving the player on the bike at the wrong
spot instead of the race start line.

The fix restores the invariant the live list always holds outside of a
load: descending CRunningScript::m_nId (a global, strictly-increasing
creation counter), which matches PS2's fresh-boot order. This test exercises
the real SortScriptListByCreationOrder() extracted from Script5.cpp.
"""
import unittest

from cpptest import compile_and_run, extract_function, harness, read_source


class ScriptLoadOrder(unittest.TestCase):
    def _run(self, main_body):
        source = read_source('stories/src/control/Script5.cpp')
        sort_fn = extract_function(source, 'static CRunningScript *SortScriptListByCreationOrder')
        # ponytail: test helper intentionally leaks its `new[]` node
        # array (freeing a singly-linked-list-turned-array is fiddly and
        # the process exits right after); silence LeakSanitizer for it.
        compile_and_run(harness('script_load_order.cpp', FUNCTION=sort_fn, MAIN_BODY=main_body),
                        env={'ASAN_OPTIONS': 'detect_leaks=0'})

    def test_reverses_ascending_save_order_into_descending(self):
        # The user's actual failing save: 75 scripts recorded in ascending
        # m_nId (govport=1 first ... margov=100 last), which is exactly the
        # reversed/broken parity that produced the mis-spawn.
        ids = [1, 9, 10, 11, 15, 16, 17, 29, 31, 32, 33, 40, 41, 42, 43, 44,
               45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
               60, 61, 71, 72, 73, 74, 78, 79, 87, 88, 89, 90, 91, 92, 93,
               95, 96, 97, 98, 99, 100]
        expected = sorted(ids, reverse=True)
        body = f'''
	int32 ids[] = {{{', '.join(str(i) for i in ids)}}};
	int n = sizeof(ids) / sizeof(ids[0]);
	CRunningScript *list = build(ids, n);
	list = SortScriptListByCreationOrder(list);
	check_consistent(list);
	int32 expected[] = {{{', '.join(str(i) for i in expected)}}};
	expect_ids(list, expected, n);
'''
        self._run(body)

    def test_already_descending_list_is_unchanged(self):
        # The good (fresh-boot / PS2) parity must round-trip as a no-op.
        ids = [100, 99, 74, 71, 54, 9, 1]
        body = f'''
	int32 ids[] = {{{', '.join(str(i) for i in ids)}}};
	int n = sizeof(ids) / sizeof(ids[0]);
	CRunningScript *list = build(ids, n);
	list = SortScriptListByCreationOrder(list);
	check_consistent(list);
	expect_ids(list, ids, n);
'''
        self._run(body)

    def test_carm_precedes_tchrm_after_sort(self):
        # Directly pins the bug: whatever order carm (m_nId=71) and tchrm
        # (m_nId=54) arrive in, carm must end up earlier in the sorted list,
        # since CARM must refresh $2289 before TCHRM reads it each frame.
        for ids in ([54, 71], [71, 54]):
            with self.subTest(ids=ids):
                body = f'''
	int32 ids[] = {{{', '.join(str(i) for i in ids)}}};
	int n = sizeof(ids) / sizeof(ids[0]);
	CRunningScript *list = build(ids, n);
	list = SortScriptListByCreationOrder(list);
	check_consistent(list);
	assert(list != nil && list->m_nId == 71);
	assert(list->next != nil && list->next->m_nId == 54);
'''
                self._run(body)

    def test_empty_and_single_element_lists(self):
        body = r'''
	CRunningScript *empty = SortScriptListByCreationOrder((CRunningScript*)nil);
	assert(empty == nil);

	int32 ids[] = {42};
	CRunningScript *one = build(ids, 1);
	one = SortScriptListByCreationOrder(one);
	check_consistent(one);
	assert(one != nil && one->m_nId == 42 && one->next == nil);
'''
        self._run(body)


if __name__ == '__main__':
    unittest.main()
