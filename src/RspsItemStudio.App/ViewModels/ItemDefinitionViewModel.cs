using RspsItemStudio.Definitions;

namespace RspsItemStudio.App.ViewModels;

public sealed class ItemDefinitionViewModel : ViewModelBase
{
    private ItemDefinitionDocument? _document;

    public ItemDefinitionViewModel()
    {
        Flags = new ItemFlagsViewModel();
        Bonuses = new CombatBonusesViewModel();
        Requirements = new LevelRequirementsViewModel();
    }

    public ItemDefinitionDocument? Document
    {
        get => _document;
        private set => SetProperty(ref _document, value);
    }

    public bool HasDocument => Document is not null;

    public string? DisplayName => Document?.Name;

    public IEnumerable<EquipmentSlot> SlotOptions => Enum.GetValues<EquipmentSlot>();

    public string Name
    {
        get => Document?.Name ?? string.Empty;
        set
        {
            if (Document is null || Document.Name == value)
                return;
            Document.Name = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(DisplayName));
        }
    }

    public string Examine
    {
        get => Document?.Examine ?? string.Empty;
        set
        {
            if (Document is null || Document.Examine == value)
                return;
            Document.Examine = value;
            OnPropertyChanged();
        }
    }

    public EquipmentSlot Slot
    {
        get => Document?.Slot ?? EquipmentSlot.None;
        set
        {
            if (Document is null || Document.Slot == value)
                return;
            Document.Slot = value;
            OnPropertyChanged();
        }
    }

    public double WeightKg
    {
        get => Document?.WeightKg ?? 0;
        set
        {
            if (Document is null || Document.WeightKg.Equals(value))
                return;
            Document.WeightKg = value;
            OnPropertyChanged();
        }
    }

    public ItemFlagsViewModel Flags { get; }
    public CombatBonusesViewModel Bonuses { get; }
    public LevelRequirementsViewModel Requirements { get; }

    public void Attach(ItemDefinitionDocument? document)
    {
        Document = document;
        Flags.Attach(document?.Flags);
        Bonuses.Attach(document?.Bonuses);
        Requirements.Attach(document?.Requirements);
        OnPropertyChanged(nameof(HasDocument));
        OnPropertyChanged(nameof(DisplayName));
        OnPropertyChanged(nameof(Name));
        OnPropertyChanged(nameof(Examine));
        OnPropertyChanged(nameof(Slot));
        OnPropertyChanged(nameof(WeightKg));
    }
}

public sealed class ItemFlagsViewModel : ViewModelBase
{
    private ItemFlags? _flags;

    public void Attach(ItemFlags? flags)
    {
        _flags = flags;
        OnPropertyChanged(nameof(Tradeable));
        OnPropertyChanged(nameof(Stackable));
        OnPropertyChanged(nameof(Noted));
        OnPropertyChanged(nameof(Members));
        OnPropertyChanged(nameof(Equipable));
    }

    public bool Tradeable
    {
        get => _flags?.Tradeable ?? false;
        set => SetFlag(value, f => f.Tradeable, nameof(Tradeable));
    }

    public bool Stackable
    {
        get => _flags?.Stackable ?? false;
        set => SetFlag(value, f => f.Stackable, nameof(Stackable));
    }

    public bool Noted
    {
        get => _flags?.Noted ?? false;
        set => SetFlag(value, f => f.Noted, nameof(Noted));
    }

    public bool Members
    {
        get => _flags?.Members ?? false;
        set => SetFlag(value, f => f.Members, nameof(Members));
    }

    public bool Equipable
    {
        get => _flags?.Equipable ?? false;
        set => SetFlag(value, f => f.Equipable, nameof(Equipable));
    }

    private void SetFlag(bool value, Func<ItemFlags, bool> getter, string propertyName)
    {
        if (_flags is null || getter(_flags) == value)
            return;
        switch (propertyName)
        {
            case nameof(Tradeable): _flags.Tradeable = value; break;
            case nameof(Stackable): _flags.Stackable = value; break;
            case nameof(Noted): _flags.Noted = value; break;
            case nameof(Members): _flags.Members = value; break;
            case nameof(Equipable): _flags.Equipable = value; break;
        }
        OnPropertyChanged(propertyName);
    }
}

public sealed class CombatBonusesViewModel : ViewModelBase
{
    private CombatBonuses? _bonuses;

    public void Attach(CombatBonuses? bonuses)
    {
        _bonuses = bonuses;
        NotifyAll();
    }

    public int AttackStab
    {
        get => _bonuses?.AttackStab ?? 0;
        set => SetBonus(b => b.AttackStab, value, nameof(AttackStab));
    }

    public int AttackSlash
    {
        get => _bonuses?.AttackSlash ?? 0;
        set => SetBonus(b => b.AttackSlash, value, nameof(AttackSlash));
    }

    public int AttackCrush
    {
        get => _bonuses?.AttackCrush ?? 0;
        set => SetBonus(b => b.AttackCrush, value, nameof(AttackCrush));
    }

    public int AttackMagic
    {
        get => _bonuses?.AttackMagic ?? 0;
        set => SetBonus(b => b.AttackMagic, value, nameof(AttackMagic));
    }

    public int AttackRanged
    {
        get => _bonuses?.AttackRanged ?? 0;
        set => SetBonus(b => b.AttackRanged, value, nameof(AttackRanged));
    }

    public int DefenceStab
    {
        get => _bonuses?.DefenceStab ?? 0;
        set => SetBonus(b => b.DefenceStab, value, nameof(DefenceStab));
    }

    public int DefenceSlash
    {
        get => _bonuses?.DefenceSlash ?? 0;
        set => SetBonus(b => b.DefenceSlash, value, nameof(DefenceSlash));
    }

    public int DefenceCrush
    {
        get => _bonuses?.DefenceCrush ?? 0;
        set => SetBonus(b => b.DefenceCrush, value, nameof(DefenceCrush));
    }

    public int DefenceMagic
    {
        get => _bonuses?.DefenceMagic ?? 0;
        set => SetBonus(b => b.DefenceMagic, value, nameof(DefenceMagic));
    }

    public int DefenceRanged
    {
        get => _bonuses?.DefenceRanged ?? 0;
        set => SetBonus(b => b.DefenceRanged, value, nameof(DefenceRanged));
    }

    public int MeleeStrength
    {
        get => _bonuses?.MeleeStrength ?? 0;
        set => SetBonus(b => b.MeleeStrength, value, nameof(MeleeStrength));
    }

    public int RangedStrength
    {
        get => _bonuses?.RangedStrength ?? 0;
        set => SetBonus(b => b.RangedStrength, value, nameof(RangedStrength));
    }

    public int MagicDamage
    {
        get => _bonuses?.MagicDamage ?? 0;
        set => SetBonus(b => b.MagicDamage, value, nameof(MagicDamage));
    }

    public int Prayer
    {
        get => _bonuses?.Prayer ?? 0;
        set => SetBonus(b => b.Prayer, value, nameof(Prayer));
    }

    private void SetBonus(Func<CombatBonuses, int> getter, int value, string propertyName)
    {
        if (_bonuses is null || getter(_bonuses) == value)
            return;
        switch (propertyName)
        {
            case nameof(AttackStab): _bonuses.AttackStab = value; break;
            case nameof(AttackSlash): _bonuses.AttackSlash = value; break;
            case nameof(AttackCrush): _bonuses.AttackCrush = value; break;
            case nameof(AttackMagic): _bonuses.AttackMagic = value; break;
            case nameof(AttackRanged): _bonuses.AttackRanged = value; break;
            case nameof(DefenceStab): _bonuses.DefenceStab = value; break;
            case nameof(DefenceSlash): _bonuses.DefenceSlash = value; break;
            case nameof(DefenceCrush): _bonuses.DefenceCrush = value; break;
            case nameof(DefenceMagic): _bonuses.DefenceMagic = value; break;
            case nameof(DefenceRanged): _bonuses.DefenceRanged = value; break;
            case nameof(MeleeStrength): _bonuses.MeleeStrength = value; break;
            case nameof(RangedStrength): _bonuses.RangedStrength = value; break;
            case nameof(MagicDamage): _bonuses.MagicDamage = value; break;
            case nameof(Prayer): _bonuses.Prayer = value; break;
        }
        OnPropertyChanged(propertyName);
    }

    private void NotifyAll()
    {
        OnPropertyChanged(nameof(AttackStab));
        OnPropertyChanged(nameof(AttackSlash));
        OnPropertyChanged(nameof(AttackCrush));
        OnPropertyChanged(nameof(AttackMagic));
        OnPropertyChanged(nameof(AttackRanged));
        OnPropertyChanged(nameof(DefenceStab));
        OnPropertyChanged(nameof(DefenceSlash));
        OnPropertyChanged(nameof(DefenceCrush));
        OnPropertyChanged(nameof(DefenceMagic));
        OnPropertyChanged(nameof(DefenceRanged));
        OnPropertyChanged(nameof(MeleeStrength));
        OnPropertyChanged(nameof(RangedStrength));
        OnPropertyChanged(nameof(MagicDamage));
        OnPropertyChanged(nameof(Prayer));
    }
}

public sealed class LevelRequirementsViewModel : ViewModelBase
{
    private LevelRequirements? _requirements;

    public void Attach(LevelRequirements? requirements)
    {
        _requirements = requirements;
        NotifyAll();
    }

    public int Attack
    {
        get => _requirements?.Attack ?? 0;
        set => SetRequirement(r => r.Attack, value, nameof(Attack));
    }

    public int Strength
    {
        get => _requirements?.Strength ?? 0;
        set => SetRequirement(r => r.Strength, value, nameof(Strength));
    }

    public int Defence
    {
        get => _requirements?.Defence ?? 0;
        set => SetRequirement(r => r.Defence, value, nameof(Defence));
    }

    public int Hitpoints
    {
        get => _requirements?.Hitpoints ?? 0;
        set => SetRequirement(r => r.Hitpoints, value, nameof(Hitpoints));
    }

    public int Ranged
    {
        get => _requirements?.Ranged ?? 0;
        set => SetRequirement(r => r.Ranged, value, nameof(Ranged));
    }

    public int Prayer
    {
        get => _requirements?.Prayer ?? 0;
        set => SetRequirement(r => r.Prayer, value, nameof(Prayer));
    }

    public int Magic
    {
        get => _requirements?.Magic ?? 0;
        set => SetRequirement(r => r.Magic, value, nameof(Magic));
    }

    private void SetRequirement(Func<LevelRequirements, int> getter, int value, string propertyName)
    {
        if (_requirements is null || getter(_requirements) == value)
            return;
        switch (propertyName)
        {
            case nameof(Attack): _requirements.Attack = value; break;
            case nameof(Strength): _requirements.Strength = value; break;
            case nameof(Defence): _requirements.Defence = value; break;
            case nameof(Hitpoints): _requirements.Hitpoints = value; break;
            case nameof(Ranged): _requirements.Ranged = value; break;
            case nameof(Prayer): _requirements.Prayer = value; break;
            case nameof(Magic): _requirements.Magic = value; break;
        }
        OnPropertyChanged(propertyName);
    }

    private void NotifyAll()
    {
        OnPropertyChanged(nameof(Attack));
        OnPropertyChanged(nameof(Strength));
        OnPropertyChanged(nameof(Defence));
        OnPropertyChanged(nameof(Hitpoints));
        OnPropertyChanged(nameof(Ranged));
        OnPropertyChanged(nameof(Prayer));
        OnPropertyChanged(nameof(Magic));
    }
}
