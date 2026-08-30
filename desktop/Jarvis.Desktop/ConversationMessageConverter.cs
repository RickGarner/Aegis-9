using System.Globalization;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Input;
using System.Windows.Media;
using Microsoft.Win32;

namespace Jarvis.Desktop;

public sealed partial class ConversationMessageConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        var message = value?.ToString() ?? string.Empty;
        var container = new StackPanel();
        var matches = FencedCodeExpression().Matches(message);
        var offset = 0;

        foreach (Match match in matches)
        {
            AddProse(container, message[offset..match.Index]);
            AddCodeBlock(container, match.Groups["language"].Value.Trim(), match.Groups["code"].Value.Trim('\r', '\n'));
            offset = match.Index + match.Length;
        }

        AddProse(container, message[offset..]);
        if (container.Children.Count == 0) AddProse(container, message);
        return container;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture) =>
        throw new NotSupportedException();

    private static void AddProse(Panel container, string text)
    {
        var normalized = text.Trim('\r', '\n');
        if (!string.IsNullOrWhiteSpace(normalized)) container.Children.Add(CreateSelectableTextBox(normalized, false));
    }

    private static void AddCodeBlock(Panel container, string language, string code)
    {
        var border = new Border
        {
            Margin = new Thickness(0, 7, 0, 7),
            Background = Brush("#D9061119"),
            BorderBrush = Brush("#7738C9EA"),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(2),
        };
        var panel = new Grid();
        panel.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        panel.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        var header = new DockPanel { Background = Brush("#B0122733"), LastChildFill = true };
        var copyButton = new Button
        {
            Content = "COPY CODE",
            Padding = new Thickness(8, 3, 8, 3),
            Margin = new Thickness(4),
            FontSize = 9,
        };
        copyButton.Click += (_, _) => Clipboard.SetText(code);
        var saveButton = new Button
        {
            Content = "SAVE AS FILE",
            Padding = new Thickness(8, 3, 8, 3),
            Margin = new Thickness(4, 4, 0, 4),
            FontSize = 9,
        };
        saveButton.Click += (_, _) => SaveCodeToFile(language, code);
        DockPanel.SetDock(saveButton, Dock.Right);
        DockPanel.SetDock(copyButton, Dock.Right);
        header.Children.Add(saveButton);
        header.Children.Add(copyButton);
        header.Children.Add(new TextBlock
        {
            Text = string.IsNullOrWhiteSpace(language) ? "CODE" : language.ToUpperInvariant(),
            Foreground = Brush("#4DE7FF"),
            FontSize = 9,
            FontWeight = FontWeights.SemiBold,
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(9, 0, 4, 0),
        });
        var codeBox = CreateSelectableTextBox(code, true);
        codeBox.Margin = new Thickness(8);
        Grid.SetRow(header, 0);
        Grid.SetRow(codeBox, 1);
        panel.Children.Add(header);
        panel.Children.Add(codeBox);
        border.Child = panel;
        container.Children.Add(border);
    }

    private static TextBox CreateSelectableTextBox(string text, bool code)
    {
        var box = new TextBox
        {
            Text = text,
            IsReadOnly = true,
            IsReadOnlyCaretVisible = true,
            Focusable = true,
            Cursor = Cursors.IBeam,
            AcceptsReturn = true,
            AcceptsTab = code,
            TextWrapping = code ? TextWrapping.NoWrap : TextWrapping.Wrap,
            Background = Brushes.Transparent,
            BorderThickness = new Thickness(0),
            Foreground = Brush(code ? "#D9F7FF" : "#E4FAFF"),
            SelectionBrush = Brush("#884DE7FF"),
            FontFamily = new FontFamily(code ? "Cascadia Mono, Consolas" : "Segoe UI"),
            FontSize = code ? 12 : 13,
            HorizontalScrollBarVisibility = code ? ScrollBarVisibility.Auto : ScrollBarVisibility.Disabled,
            VerticalScrollBarVisibility = ScrollBarVisibility.Disabled,
        };
        var menu = new ContextMenu();
        var copy = new MenuItem { Header = "COPY SELECTED TEXT" };
        copy.Click += (_, _) =>
        {
            var selected = string.IsNullOrEmpty(box.SelectedText) ? box.Text : box.SelectedText;
            if (!string.IsNullOrEmpty(selected)) Clipboard.SetText(selected);
        };
        menu.Items.Add(copy);
        box.ContextMenu = menu;
        return box;
    }

    private static SolidColorBrush Brush(string color) => new((Color)ColorConverter.ConvertFromString(color));

    private static void SaveCodeToFile(string language, string code)
    {
        var (extension, description, suggestedName) = CodeFileType(language);
        var dialog = new SaveFileDialog
        {
            Title = "Save generated code",
            FileName = suggestedName,
            DefaultExt = extension,
            AddExtension = true,
            OverwritePrompt = true,
            Filter = $"{description} (*{extension})|*{extension}|All files (*.*)|*.*",
        };
        if (dialog.ShowDialog() != true) return;
        try
        {
            File.WriteAllText(dialog.FileName, code, new UTF8Encoding(false));
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException)
        {
            MessageBox.Show(
                $"A.E.G.I.S.-9 could not save the generated code.\n\n{error.Message}",
                "Save generated code",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
    }

    private static (string Extension, string Description, string SuggestedName) CodeFileType(string language)
    {
        return language.Trim().ToLowerInvariant() switch
        {
            "powershell" or "ps1" => (".ps1", "PowerShell scripts", "GeneratedScript.ps1"),
            "python" or "py" => (".py", "Python files", "generated_code.py"),
            "c#" or "csharp" or "cs" => (".cs", "C# source files", "GeneratedCode.cs"),
            "javascript" or "js" => (".js", "JavaScript files", "generated-code.js"),
            "typescript" or "ts" => (".ts", "TypeScript files", "generated-code.ts"),
            "json" => (".json", "JSON files", "generated-data.json"),
            "sql" => (".sql", "SQL scripts", "generated-script.sql"),
            "batch" or "bat" or "cmd" => (".bat", "Windows batch files", "GeneratedScript.bat"),
            "bash" or "shell" or "sh" => (".sh", "Shell scripts", "generated-script.sh"),
            "xml" => (".xml", "XML files", "generated-data.xml"),
            "yaml" or "yml" => (".yaml", "YAML files", "generated-config.yaml"),
            "html" => (".html", "HTML files", "generated-page.html"),
            "css" => (".css", "CSS files", "generated-style.css"),
            _ => (".txt", "Text files", "generated-code.txt"),
        };
    }

    [GeneratedRegex("```(?<language>[^\\r\\n`]*)\\r?\\n(?<code>[\\s\\S]*?)```", RegexOptions.CultureInvariant)]
    private static partial Regex FencedCodeExpression();
}
