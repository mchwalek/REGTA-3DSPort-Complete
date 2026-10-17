import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.Function;

public class Decomp extends GhidraScript {
	@Override
	public void run() throws Exception {
		println("LANG=" + currentProgram.getLanguageID());
		DecompInterface d = new DecompInterface();
		d.openProgram(currentProgram);
		for (String a : getScriptArgs()) {
			Function f = getFunctionAt(toAddr(a));
			if (f == null)
				f = createFunction(toAddr(a), null);
			DecompileResults r = d.decompileFunction(f, 120, monitor);
			println("=== " + a + "\n" + (r.decompileCompleted() ? r.getDecompiledFunction().getC() : r.getErrorMessage()));
		}
	}
}
