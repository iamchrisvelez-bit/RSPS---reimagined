package net.runelite.cache.definitions;

/** Minimal item definition: only the fields ItemSpriteFactory reads (the full
 *  RuneLite class needs Lombok and the entity-ops classes). */
public class ItemDefinition
{
	public final int id;
	public int inventoryModel = -1;
	public int zoom2d = 2000, xan2d = 0, yan2d = 0, zan2d = 0, xOffset2d = 0, yOffset2d = 0;
	public int resizeX = 128, resizeY = 128, resizeZ = 128;
	public int ambient = 0, contrast = 0;
	public short[] colorFind, colorReplace, textureFind, textureReplace;
	public int[] countObj, countCo;
	public int notedID = -1, notedTemplate = -1, boughtId = -1, boughtTemplateId = -1;
	public int placeholderId = -1, placeholderTemplateId = -1;
	public int stackable = 0;
	public String name = "null";

	public ItemDefinition(int id)
	{
		this.id = id;
	}
}
