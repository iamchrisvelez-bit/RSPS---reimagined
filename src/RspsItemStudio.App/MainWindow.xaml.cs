using System.Windows;
using RspsItemStudio.App.ViewModels;

namespace RspsItemStudio.App;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        DataContext = new MainViewModel();
    }

    private void OnExitClick(object sender, RoutedEventArgs e) => Close();
}
