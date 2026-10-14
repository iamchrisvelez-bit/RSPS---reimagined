import java.nio.file.*;
import java.util.*;
import net.runelite.cache.definitions.ModelDefinition;
import net.runelite.cache.definitions.loaders.ModelLoader;

/** Decodes model files (any format: old, type 1/2/3) with RuneLite's ModelLoader
 *  and prints one JSON object per line: vertices, faces, colours, render
 *  types, priorities, alphas, textures, vertex groups (skins) and whether the
 *  model has animaya (skeletal) weights.
 *  usage: java ModelDump <file.dat>...   (the model id is the file name) */
public class ModelDump {
    static void arr(StringBuilder sb, String k, int n, java.util.function.IntUnaryOperator f) {
        sb.append(",\"").append(k).append("\":[");
        for (int i = 0; i < n; i++) { if (i > 0) sb.append(','); sb.append(f.applyAsInt(i)); }
        sb.append(']');
    }
    public static void main(String[] a) throws Exception {
        for (String p : a) {
            Path path = Paths.get(p);
            int id = Integer.parseInt(path.getFileName().toString().replaceAll("\\..*", ""));
            ModelDefinition d = new ModelLoader().load(id, Files.readAllBytes(path));
            StringBuilder sb = new StringBuilder();
            sb.append("{\"id\":").append(id).append(",\"nv\":").append(d.vertexCount).append(",\"nf\":").append(d.faceCount)
              .append(",\"priority\":").append(d.priority);
            int nv = d.vertexCount, nf = d.faceCount;
            arr(sb, "x", nv, i -> d.vertexX[i]);
            arr(sb, "y", nv, i -> d.vertexY[i]);
            arr(sb, "z", nv, i -> d.vertexZ[i]);
            arr(sb, "f1", nf, i -> d.faceIndices1[i]);
            arr(sb, "f2", nf, i -> d.faceIndices2[i]);
            arr(sb, "f3", nf, i -> d.faceIndices3[i]);
            arr(sb, "col", nf, i -> d.faceColors[i] & 0xFFFF);
            if (d.faceRenderTypes != null) arr(sb, "rtype", nf, i -> d.faceRenderTypes[i]);
            if (d.faceRenderPriorities != null) arr(sb, "prio", nf, i -> d.faceRenderPriorities[i]);
            if (d.faceTransparencies != null) arr(sb, "alpha", nf, i -> d.faceTransparencies[i] & 0xFF);
            if (d.faceTextures != null) arr(sb, "tex", nf, i -> d.faceTextures[i]);
            // load() packs the per-vertex labels into vertexGroups (label -> vertices) and
            // drops packedVertexGroups; unpack them again
            java.lang.reflect.Field g = ModelDefinition.class.getDeclaredField("vertexGroups");
            g.setAccessible(true);
            int[][] groups = (int[][]) g.get(d);
            if (groups != null) {
                int[] label = new int[nv];
                for (int k = 0; k < groups.length; k++) for (int v : groups[k]) label[v] = k;
                arr(sb, "vgroup", nv, i -> label[i]);
            }
            sb.append(",\"animaya\":").append(d.animayaGroups != null);
            sb.append('}');
            System.out.println(sb);
        }
    }
}
