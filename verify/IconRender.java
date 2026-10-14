import java.awt.image.BufferedImage;
import java.io.File;
import java.nio.file.*;
import javax.imageio.ImageIO;
import net.runelite.cache.definitions.ItemDefinition;
import net.runelite.cache.definitions.ModelDefinition;
import net.runelite.cache.definitions.loaders.ModelLoader;
import net.runelite.cache.item.ItemSpriteFactory;

/** Renders a 36x32 inventory icon exactly as the client does (RuneLite's port
 *  of the client's item sprite code: lighting, zoom2d/xan2d/yan2d framing,
 *  1px black outline and drop shadow).
 *  usage: java IconRender model.dat out.png zoom2d xan2d yan2d zan2d xOffset2d yOffset2d
 *                         [resizeX resizeY resizeZ ambient contrast] */
public class IconRender {
    public static void main(String[] a) throws Exception {
        byte[] data = Files.readAllBytes(Paths.get(a[0]));
        ItemDefinition def = new ItemDefinition(0);
        def.inventoryModel = 0;
        def.zoom2d = Integer.parseInt(a[2]);
        def.xan2d = Integer.parseInt(a[3]);
        def.yan2d = Integer.parseInt(a[4]);
        def.zan2d = Integer.parseInt(a[5]);
        def.xOffset2d = Integer.parseInt(a[6]);
        def.yOffset2d = Integer.parseInt(a[7]);
        if (a.length > 8) {
            def.resizeX = Integer.parseInt(a[8]);
            def.resizeY = Integer.parseInt(a[9]);
            def.resizeZ = Integer.parseInt(a[10]);
            def.ambient = Integer.parseInt(a[11]);
            def.contrast = Integer.parseInt(a[12]);
        }
        BufferedImage img;
        try {
            img = render(def, data, false);
        } catch (RuntimeException e) {
            // textured faces need the cache's texture sprites, which this tool
            // doesn't load: draw them in their face colour instead (the
            // silhouette and framing are unchanged)
            img = render(def, data, true);
            System.err.println("textures drawn as flat colour");
        }
        ImageIO.write(img, "png", new File(a[1]));
    }

    static BufferedImage render(ItemDefinition def, byte[] data, boolean stripTextures) throws Exception {
        return ItemSpriteFactory.createSprite(
            id -> def,
            id -> {
                ModelDefinition m = new ModelLoader().load(id, data);
                if (stripTextures) {
                    m.faceTextures = null;
                    m.textureCoords = null;
                }
                return m;
            },
            (id, frame) -> null,
            () -> new net.runelite.cache.definitions.TextureDefinition[0],
            0, 1, 1, 0x302020, false);
    }
}
