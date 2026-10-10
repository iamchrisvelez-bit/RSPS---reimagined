import java.nio.file.*;
import java.util.*;
import net.runelite.cache.definitions.ModelDefinition;
import net.runelite.cache.definitions.loaders.ModelLoader;

/** Decodes every model with RuneLite's own ModelLoader and prints a canonical
 *  dump (id, counts, vertices, faces, colours, render types) for comparison. */
public class VerifyModels {
    public static void main(String[] a) throws Exception {
        Path dir = Paths.get(a[0]);
        List<Path> files = new ArrayList<>();
        try (DirectoryStream<Path> ds = Files.newDirectoryStream(dir, "*.dat")) { for (Path p : ds) files.add(p); }
        Collections.sort(files);
        StringBuilder sb = new StringBuilder();
        for (Path p : files) {
            int id = Integer.parseInt(p.getFileName().toString().replace(".dat", ""));
            ModelDefinition d = new ModelLoader().load(id, Files.readAllBytes(p));
            sb.append("M ").append(id).append(' ').append(d.vertexCount).append(' ').append(d.faceCount).append('\n');
            for (int i = 0; i < d.vertexCount; i++)
                sb.append("v ").append(d.vertexX[i]).append(' ').append(d.vertexY[i]).append(' ').append(d.vertexZ[i]).append('\n');
            for (int i = 0; i < d.faceCount; i++)
                sb.append("f ").append(d.faceIndices1[i]).append(' ').append(d.faceIndices2[i]).append(' ').append(d.faceIndices3[i])
                  .append(' ').append(d.faceColors[i] & 0xFFFF)
                  .append(' ').append(d.faceRenderTypes == null ? 0 : d.faceRenderTypes[i])
                  .append(' ').append(d.faceTextures == null ? -1 : d.faceTextures[i]).append('\n');
            d.computeNormals();
        }
        System.out.print(sb);
    }
}
