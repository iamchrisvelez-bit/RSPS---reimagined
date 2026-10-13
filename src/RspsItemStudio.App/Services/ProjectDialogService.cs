using System.IO;
using System.Windows;
using Microsoft.Win32;
using RspsItemStudio.Core.Projects;

namespace RspsItemStudio.App.Services;

public sealed class ProjectDialogService
{
    public bool TryPickNewProjectLocation(out string? projectRoot, out string? displayName)
    {
        projectRoot = null;
        displayName = null;

        var parentDialog = new OpenFolderDialog
        {
            Title = "Choose folder for the new item project",
            Multiselect = false
        };

        if (parentDialog.ShowDialog() != true)
            return false;

        var parent = parentDialog.FolderName;
        if (string.IsNullOrWhiteSpace(parent))
            return false;

        if (!TryPromptText(
                "New item project",
                "Display name for this item:",
                "New Item",
                out var name))
            return false;

        displayName = name.Trim();
        if (string.IsNullOrEmpty(displayName))
            return false;

        var folderName = SanitizeFolderName(displayName);
        projectRoot = Path.Combine(parent, folderName);
        return true;
    }

    public bool TryPickExistingProjectRoot(out string? projectRoot)
    {
        projectRoot = null;

        var dialog = new OpenFolderDialog
        {
            Title = "Open item project folder (contains itemstudio.json)",
            Multiselect = false
        };

        if (dialog.ShowDialog() != true)
            return false;

        var folder = dialog.FolderName;
        if (string.IsNullOrWhiteSpace(folder))
            return false;

        var manifestPath = Path.Combine(folder, ItemProjectPaths.Manifest);
        if (!File.Exists(manifestPath))
        {
            MessageBox.Show(
                $"This folder does not contain {ItemProjectPaths.Manifest}.",
                "RSPS Item Studio",
                MessageBoxButton.OK,
                MessageBoxImage.Warning);
            return false;
        }

        projectRoot = folder;
        return true;
    }

    private static bool TryPromptText(string title, string prompt, string defaultText, out string? result)
    {
        result = null;
        var dialog = new Window
        {
            Title = title,
            Width = 420,
            Height = 160,
            WindowStartupLocation = WindowStartupLocation.CenterScreen,
            ResizeMode = ResizeMode.NoResize
        };

        var promptBlock = new System.Windows.Controls.TextBlock
        {
            Text = prompt,
            Margin = new Thickness(12, 12, 12, 0)
        };

        var input = new System.Windows.Controls.TextBox
        {
            Text = defaultText,
            Margin = new Thickness(12, 8, 12, 0)
        };

        var ok = new System.Windows.Controls.Button
        {
            Content = "OK",
            IsDefault = true,
            Width = 80,
            Margin = new Thickness(0, 0, 8, 0)
        };

        var cancel = new System.Windows.Controls.Button
        {
            Content = "Cancel",
            IsCancel = true,
            Width = 80
        };

        var buttons = new System.Windows.Controls.StackPanel
        {
            Orientation = System.Windows.Controls.Orientation.Horizontal,
            HorizontalAlignment = HorizontalAlignment.Right,
            Margin = new Thickness(12)
        };
        buttons.Children.Add(ok);
        buttons.Children.Add(cancel);

        var layout = new System.Windows.Controls.Grid();
        layout.RowDefinitions.Add(new System.Windows.Controls.RowDefinition { Height = GridLength.Auto });
        layout.RowDefinitions.Add(new System.Windows.Controls.RowDefinition { Height = GridLength.Auto });
        layout.RowDefinitions.Add(new System.Windows.Controls.RowDefinition { Height = GridLength.Auto });
        System.Windows.Controls.Grid.SetRow(promptBlock, 0);
        System.Windows.Controls.Grid.SetRow(input, 1);
        System.Windows.Controls.Grid.SetRow(buttons, 2);
        layout.Children.Add(promptBlock);
        layout.Children.Add(input);
        layout.Children.Add(buttons);
        dialog.Content = layout;

        ok.Click += (_, _) =>
        {
            result = input.Text;
            dialog.DialogResult = true;
        };

        if (dialog.ShowDialog() != true)
            return false;

        result = input.Text;
        return !string.IsNullOrWhiteSpace(result);
    }

    private static string SanitizeFolderName(string displayName)
    {
        var invalid = Path.GetInvalidFileNameChars();
        var chars = displayName.Trim().Select(c => invalid.Contains(c) ? '_' : c).ToArray();
        var name = new string(chars).Trim();
        return string.IsNullOrEmpty(name) ? "NewItem" : name;
    }
}
