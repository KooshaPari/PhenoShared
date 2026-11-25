import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { exec, spawn } from 'child_process';
import { WebSocket } from 'ws';

// Main extension class
export class KodeVibeExtension {
    private context: vscode.ExtensionContext;
    private diagnosticCollection: vscode.DiagnosticCollection;
    private statusBarItem: vscode.StatusBarItem;
    private outputChannel: vscode.OutputChannel;
    private webSocket?: WebSocket;
    private lastAnalysisResult?: AnalysisResult;
    private issuesProvider: IssuesProvider;
    private vibesProvider: VibesProvider;
    private metricsProvider: MetricsProvider;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('kodevibe');
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left);
        this.outputChannel = vscode.window.createOutputChannel('KodeVibe');
        
        // Initialize tree providers
        this.issuesProvider = new IssuesProvider();
        this.vibesProvider = new VibesProvider();
        this.metricsProvider = new MetricsProvider();
        
        this.setupCommands();
        this.setupTreeViews();
        this.setupStatusBar();
        this.setupFileWatchers();
        
        // Check for KodeVibe executable
        this.checkKodeVibeInstallation();
    }

    private setupCommands() {
        const commands = [
            vscode.commands.registerCommand('kodevibe.analyze', () => this.analyzeWorkspace()),
            vscode.commands.registerCommand('kodevibe.analyzeFile', () => this.analyzeCurrentFile()),
            vscode.commands.registerCommand('kodevibe.showReport', () => this.showReport()),
            vscode.commands.registerCommand('kodevibe.configure', () => this.configure()),
            vscode.commands.registerCommand('kodevibe.fixIssue', (issue: Issue) => this.fixIssue(issue)),
            vscode.commands.registerCommand('kodevibe.enableRealtime', () => this.toggleRealtime()),
        ];

        commands.forEach(command => this.context.subscriptions.push(command));
    }

    private setupTreeViews() {
        vscode.window.createTreeView('kodevibe-issues', {
            treeDataProvider: this.issuesProvider,
            showCollapseAll: true
        });

        vscode.window.createTreeView('kodevibe-vibes', {
            treeDataProvider: this.vibesProvider,
            showCollapseAll: true
        });

        vscode.window.createTreeView('kodevibe-metrics', {
            treeDataProvider: this.metricsProvider,
            showCollapseAll: true
        });
    }

    private setupStatusBar() {
        this.statusBarItem.text = "$(wave) KodeVibe";
        this.statusBarItem.tooltip = "Click to analyze workspace";
        this.statusBarItem.command = 'kodevibe.analyze';
        this.statusBarItem.show();
        this.context.subscriptions.push(this.statusBarItem);
    }

    private setupFileWatchers() {
        const config = vscode.workspace.getConfiguration('kodevibe');
        if (config.get('enableRealtime')) {
            this.enableRealtimeAnalysis();
        }

        // Watch for configuration changes
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('kodevibe.enableRealtime')) {
                const enabled = vscode.workspace.getConfiguration('kodevibe').get('enableRealtime');
                if (enabled) {
                    this.enableRealtimeAnalysis();
                } else {
                    this.disableRealtimeAnalysis();
                }
            }
        });
    }

    private async checkKodeVibeInstallation() {
        const config = vscode.workspace.getConfiguration('kodevibe');
        const executablePath = config.get<string>('executablePath') || 'kodevibe';

        return new Promise<boolean>((resolve) => {
            exec(`${executablePath} --version`, (error) => {
                if (error) {
                    this.showInstallationPrompt();
                    resolve(false);
                } else {
                    resolve(true);
                }
            });
        });
    }

    private async showInstallationPrompt() {
        const choice = await vscode.window.showWarningMessage(
            'KodeVibe executable not found. Would you like to install it?',
            'Install', 'Configure Path', 'Dismiss'
        );

        switch (choice) {
            case 'Install':
                this.installKodeVibe();
                break;
            case 'Configure Path':
                this.configureExecutablePath();
                break;
        }
    }

    private async installKodeVibe() {
        vscode.window.showInformationMessage('Opening KodeVibe installation guide...');
        vscode.env.openExternal(vscode.Uri.parse('https://github.com/kooshapari/kodevibe-go#installation'));
    }

    private async configureExecutablePath() {
        const path = await vscode.window.showInputBox({
            prompt: 'Enter the path to KodeVibe executable',
            placeHolder: '/usr/local/bin/kodevibe'
        });

        if (path) {
            const config = vscode.workspace.getConfiguration('kodevibe');
            await config.update('executablePath', path, vscode.ConfigurationTarget.Workspace);
        }
    }

    private async analyzeWorkspace() {
        if (!vscode.workspace.workspaceFolders) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }

        const workspaceRoot = vscode.workspace.workspaceFolders[0].uri.fsPath;
        this.statusBarItem.text = "$(sync~spin) Analyzing...";
        
        try {
            const result = await this.runAnalysis(workspaceRoot);
            await this.processAnalysisResult(result);
            this.statusBarItem.text = "$(check) Analysis Complete";
            
            setTimeout(() => {
                this.statusBarItem.text = "$(wave) KodeVibe";
            }, 3000);
        } catch (error) {
            this.statusBarItem.text = "$(error) Analysis Failed";
            vscode.window.showErrorMessage(`Analysis failed: ${error}`);
            
            setTimeout(() => {
                this.statusBarItem.text = "$(wave) KodeVibe";
            }, 3000);
        }
    }

    private async analyzeCurrentFile() {
        const activeEditor = vscode.window.activeTextEditor;
        if (!activeEditor) {
            vscode.window.showErrorMessage('No active file');
            return;
        }

        const filePath = activeEditor.document.fileName;
        this.statusBarItem.text = "$(sync~spin) Analyzing File...";

        try {
            const result = await this.runAnalysis(filePath, ['--file']);
            await this.processAnalysisResult(result, filePath);
            this.statusBarItem.text = "$(check) File Analyzed";
            
            setTimeout(() => {
                this.statusBarItem.text = "$(wave) KodeVibe";
            }, 3000);
        } catch (error) {
            this.statusBarItem.text = "$(error) Analysis Failed";
            vscode.window.showErrorMessage(`File analysis failed: ${error}`);
        }
    }

    private async runAnalysis(targetPath: string, extraArgs: string[] = []): Promise<AnalysisResult> {
        const config = vscode.workspace.getConfiguration('kodevibe');
        const executablePath = config.get<string>('executablePath') || 'kodevibe';
        const vibes = config.get<string[]>('vibes') || ['security', 'performance', 'readability'];
        
        const args = [
            'analyze',
            ...vibes.flatMap(vibe => ['--vibe', vibe]),
            '--output', 'json',
            ...extraArgs,
            targetPath
        ];

        return new Promise((resolve, reject) => {
            const process = spawn(executablePath, args);
            let stdout = '';
            let stderr = '';

            process.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            process.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            process.on('close', (code) => {
                if (code === 0) {
                    try {
                        const result = JSON.parse(stdout);
                        resolve(result);
                    } catch (error) {
                        reject(`Failed to parse analysis result: ${error}`);
                    }
                } else {
                    reject(`Analysis failed with code ${code}: ${stderr}`);
                }
            });

            process.on('error', (error) => {
                reject(`Failed to start analysis: ${error}`);
            });
        });
    }

    private async processAnalysisResult(result: AnalysisResult, singleFile?: string) {
        this.lastAnalysisResult = result;
        
        // Update diagnostics
        this.updateDiagnostics(result, singleFile);
        
        // Update tree views
        this.updateTreeViews(result);
        
        // Update context
        vscode.commands.executeCommand('setContext', 'kodevibe:hasIssues', result.issues.length > 0);
        vscode.commands.executeCommand('setContext', 'kodevibe:hasAnalysis', true);
        
        // Show summary
        this.showAnalysisSummary(result);
        
        // Log to output channel
        this.outputChannel.appendLine(`Analysis completed: ${result.issues.length} issues found`);
        this.outputChannel.appendLine(`Overall score: ${result.overallScore.toFixed(1)}/100`);
    }

    private updateDiagnostics(result: AnalysisResult, singleFile?: string) {
        const config = vscode.workspace.getConfiguration('kodevibe');
        const showInProblems = config.get<boolean>('showInProblems', true);
        
        if (!showInProblems) {
            return;
        }

        // Clear existing diagnostics
        if (singleFile) {
            this.diagnosticCollection.set(vscode.Uri.file(singleFile), []);
        } else {
            this.diagnosticCollection.clear();
        }

        // Group issues by file
        const issuesByFile = new Map<string, Issue[]>();
        result.issues.forEach(issue => {
            if (!issuesByFile.has(issue.file)) {
                issuesByFile.set(issue.file, []);
            }
            issuesByFile.get(issue.file)!.push(issue);
        });

        // Create diagnostics for each file
        issuesByFile.forEach((issues, filePath) => {
            const diagnostics = issues.map(issue => this.createDiagnostic(issue));
            this.diagnosticCollection.set(vscode.Uri.file(filePath), diagnostics);
        });
    }

    private createDiagnostic(issue: Issue): vscode.Diagnostic {
        const line = Math.max(0, issue.line - 1);
        const range = new vscode.Range(line, 0, line, Number.MAX_SAFE_INTEGER);
        
        const diagnostic = new vscode.Diagnostic(
            range,
            `[${issue.category || 'general'}] ${issue.message}`,
            this.getSeverity(issue.severity)
        );
        
        diagnostic.source = 'KodeVibe';
        diagnostic.code = issue.rule || '';
        
        // Add fix if available
        if (issue.fix) {
            diagnostic.tags = [vscode.DiagnosticTag.Unnecessary];
        }
        
        return diagnostic;
    }

    private getSeverity(severity: string): vscode.DiagnosticSeverity {
        switch (severity.toLowerCase()) {
            case 'high':
            case 'error':
                return vscode.DiagnosticSeverity.Error;
            case 'medium':
            case 'warning':
                return vscode.DiagnosticSeverity.Warning;
            case 'low':
            case 'info':
                return vscode.DiagnosticSeverity.Information;
            default:
                return vscode.DiagnosticSeverity.Hint;
        }
    }

    private updateTreeViews(result: AnalysisResult) {
        this.issuesProvider.update(result.issues);
        this.vibesProvider.update(result.vibeResults);
        this.metricsProvider.update(result);
    }

    private showAnalysisSummary(result: AnalysisResult) {
        const issueCount = result.issues.length;
        const score = result.overallScore.toFixed(1);
        
        if (issueCount === 0) {
            vscode.window.showInformationMessage(`🎉 Analysis complete! Score: ${score}/100. No issues found.`);
        } else {
            const message = `Analysis complete! Score: ${score}/100. Found ${issueCount} issue${issueCount === 1 ? '' : 's'}.`;
            vscode.window.showWarningMessage(message, 'Show Report', 'View Issues').then(choice => {
                if (choice === 'Show Report') {
                    this.showReport();
                } else if (choice === 'View Issues') {
                    vscode.commands.executeCommand('workbench.panel.markers.view.focus');
                }
            });
        }
    }

    private async showReport() {
        if (!this.lastAnalysisResult) {
            vscode.window.showErrorMessage('No analysis results available. Run an analysis first.');
            return;
        }

        // Generate HTML report
        const reportHtml = this.generateReportHtml(this.lastAnalysisResult);
        
        // Create webview
        const panel = vscode.window.createWebviewPanel(
            'kodevibeReport',
            'KodeVibe Analysis Report',
            vscode.ViewColumn.Beside,
            {
                enableScripts: true,
                localResourceRoots: [this.context.extensionUri]
            }
        );

        panel.webview.html = reportHtml;
    }

    private generateReportHtml(result: AnalysisResult): string {
        return `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KodeVibe Analysis Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
        }
        .header {
            border-bottom: 1px solid var(--vscode-panel-border);
            padding-bottom: 20px;
            margin-bottom: 20px;
        }
        .score {
            font-size: 2em;
            font-weight: bold;
            color: var(--vscode-charts-green);
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .metric {
            background: var(--vscode-editor-widget-background);
            border: 1px solid var(--vscode-panel-border);
            padding: 15px;
            border-radius: 5px;
        }
        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
        }
        .issues {
            margin-top: 20px;
        }
        .issue {
            background: var(--vscode-editor-widget-background);
            border-left: 4px solid var(--vscode-errorForeground);
            padding: 10px;
            margin: 10px 0;
        }
        .issue.warning {
            border-left-color: var(--vscode-warningForeground);
        }
        .issue.info {
            border-left-color: var(--vscode-infoForeground);
        }
        .vibes {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .vibe {
            background: var(--vscode-editor-widget-background);
            border: 1px solid var(--vscode-panel-border);
            padding: 15px;
            border-radius: 5px;
        }
        .vibe-score {
            font-size: 1.2em;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌊 KodeVibe Analysis Report</h1>
        <div class="score">Overall Score: ${result.overallScore.toFixed(1)}/100</div>
    </div>
    
    <div class="metrics">
        <div class="metric">
            <div class="metric-value">${result.filesAnalyzed}</div>
            <div>Files Analyzed</div>
        </div>
        <div class="metric">
            <div class="metric-value">${result.linesAnalyzed}</div>
            <div>Lines of Code</div>
        </div>
        <div class="metric">
            <div class="metric-value">${result.issues.length}</div>
            <div>Issues Found</div>
        </div>
        <div class="metric">
            <div class="metric-value">${(result.duration / 1000000).toFixed(2)}s</div>
            <div>Analysis Time</div>
        </div>
    </div>
    
    <h2>Vibes Analysis</h2>
    <div class="vibes">
        ${result.vibeResults.map(vibe => `
            <div class="vibe">
                <h3>${vibe.name.charAt(0).toUpperCase() + vibe.name.slice(1)}</h3>
                <div class="vibe-score">${vibe.score.toFixed(1)}/100</div>
                ${vibe.details ? `<p>${vibe.details}</p>` : ''}
            </div>
        `).join('')}
    </div>
    
    ${result.issues.length > 0 ? `
        <h2>Issues (${result.issues.length})</h2>
        <div class="issues">
            ${result.issues.map(issue => `
                <div class="issue ${issue.severity}">
                    <strong>${issue.file}:${issue.line}</strong> - ${issue.severity.toUpperCase()}
                    <br>${issue.message}
                    ${issue.fix ? `<br><em>Suggested fix: ${issue.fix}</em>` : ''}
                </div>
            `).join('')}
        </div>
    ` : '<h2>🎉 No issues found!</h2>'}
</body>
</html>
        `;
    }

    private async configure() {
        const actions = [
            'Select Vibes',
            'Configure Severity',
            'Toggle Real-time Analysis',
            'Set Executable Path'
        ];

        const choice = await vscode.window.showQuickPick(actions, {
            placeHolder: 'Choose configuration option'
        });

        switch (choice) {
            case 'Select Vibes':
                await this.configureVibes();
                break;
            case 'Configure Severity':
                await this.configureSeverity();
                break;
            case 'Toggle Real-time Analysis':
                await this.toggleRealtime();
                break;
            case 'Set Executable Path':
                await this.configureExecutablePath();
                break;
        }
    }

    private async configureVibes() {
        const availableVibes = ['security', 'performance', 'readability', 'maintainability', 'testing', 'documentation', 'complexity'];
        const config = vscode.workspace.getConfiguration('kodevibe');
        const currentVibes = config.get<string[]>('vibes') || [];

        const selectedVibes = await vscode.window.showQuickPick(
            availableVibes.map(vibe => ({
                label: vibe.charAt(0).toUpperCase() + vibe.slice(1),
                picked: currentVibes.includes(vibe)
            })),
            {
                canPickMany: true,
                placeHolder: 'Select vibes to analyze'
            }
        );

        if (selectedVibes) {
            const vibes = selectedVibes.map(item => item.label.toLowerCase());
            await config.update('vibes', vibes, vscode.ConfigurationTarget.Workspace);
            vscode.window.showInformationMessage(`Updated vibes: ${vibes.join(', ')}`);
        }
    }

    private async configureSeverity() {
        const severities = ['low', 'medium', 'high'];
        const config = vscode.workspace.getConfiguration('kodevibe');
        const currentSeverity = config.get<string>('severity');

        const choice = await vscode.window.showQuickPick(
            severities.map(severity => ({
                label: severity.charAt(0).toUpperCase() + severity.slice(1),
                picked: severity === currentSeverity
            })),
            {
                placeHolder: 'Select minimum severity level'
            }
        );

        if (choice) {
            await config.update('severity', choice.label.toLowerCase(), vscode.ConfigurationTarget.Workspace);
            vscode.window.showInformationMessage(`Updated minimum severity: ${choice.label}`);
        }
    }

    private async toggleRealtime() {
        const config = vscode.workspace.getConfiguration('kodevibe');
        const current = config.get<boolean>('enableRealtime');
        
        await config.update('enableRealtime', !current, vscode.ConfigurationTarget.Workspace);
        vscode.window.showInformationMessage(`Real-time analysis ${!current ? 'enabled' : 'disabled'}`);
    }

    private async fixIssue(issue: Issue) {
        if (!issue.fix) {
            vscode.window.showErrorMessage('No automated fix available for this issue');
            return;
        }

        const document = await vscode.workspace.openTextDocument(issue.file);
        const edit = new vscode.WorkspaceEdit();
        
        // Apply the fix (this is a simplified implementation)
        const line = document.lineAt(issue.line - 1);
        edit.replace(document.uri, line.range, issue.fix);
        
        const success = await vscode.workspace.applyEdit(edit);
        if (success) {
            vscode.window.showInformationMessage('Fix applied successfully');
        } else {
            vscode.window.showErrorMessage('Failed to apply fix');
        }
    }

    private enableRealtimeAnalysis() {
        // Watch for file changes
        const watcher = vscode.workspace.createFileSystemWatcher('**/*.{js,ts,py,go,java,rs}');
        
        watcher.onDidChange(uri => {
            // Debounce analysis
            setTimeout(() => this.analyzeFile(uri.fsPath), 1000);
        });

        this.context.subscriptions.push(watcher);
    }

    private disableRealtimeAnalysis() {
        // Real-time analysis is disabled through configuration change handling
    }

    private async analyzeFile(filePath: string) {
        try {
            const result = await this.runAnalysis(filePath, ['--file']);
            this.updateDiagnostics(result, filePath);
        } catch (error) {
            // Silently fail for real-time analysis
            this.outputChannel.appendLine(`Real-time analysis failed for ${filePath}: ${error}`);
        }
    }

    dispose() {
        this.diagnosticCollection.dispose();
        this.statusBarItem.dispose();
        this.outputChannel.dispose();
        if (this.webSocket) {
            this.webSocket.close();
        }
    }
}

// Tree data providers
class IssuesProvider implements vscode.TreeDataProvider<Issue> {
    private _onDidChangeTreeData = new vscode.EventEmitter<Issue | undefined | null | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
    private issues: Issue[] = [];

    update(issues: Issue[]) {
        this.issues = issues;
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: Issue): vscode.TreeItem {
        const item = new vscode.TreeItem(
            `${path.basename(element.file)}:${element.line}`,
            vscode.TreeItemCollapsibleState.None
        );
        
        item.description = element.message;
        item.tooltip = `${element.file}:${element.line}\n${element.message}`;
        item.command = {
            command: 'vscode.open',
            title: 'Open File',
            arguments: [vscode.Uri.file(element.file), { selection: new vscode.Range(element.line - 1, 0, element.line - 1, 0) }]
        };
        
        // Set icon based on severity
        switch (element.severity) {
            case 'high':
                item.iconPath = new vscode.ThemeIcon('error', new vscode.ThemeColor('errorForeground'));
                break;
            case 'medium':
                item.iconPath = new vscode.ThemeIcon('warning', new vscode.ThemeColor('warningForeground'));
                break;
            default:
                item.iconPath = new vscode.ThemeIcon('info', new vscode.ThemeColor('infoForeground'));
        }
        
        return item;
    }

    getChildren(element?: Issue): Issue[] {
        if (!element) {
            return this.issues;
        }
        return [];
    }
}

class VibesProvider implements vscode.TreeDataProvider<VibeResult> {
    private _onDidChangeTreeData = new vscode.EventEmitter<VibeResult | undefined | null | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
    private vibes: VibeResult[] = [];

    update(vibes: VibeResult[]) {
        this.vibes = vibes;
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: VibeResult): vscode.TreeItem {
        const item = new vscode.TreeItem(
            element.name.charAt(0).toUpperCase() + element.name.slice(1),
            vscode.TreeItemCollapsibleState.None
        );
        
        item.description = `${element.score.toFixed(1)}/100`;
        item.tooltip = element.details || `${element.name}: ${element.score.toFixed(1)}/100`;
        
        // Set icon based on score
        if (element.score >= 90) {
            item.iconPath = new vscode.ThemeIcon('check', new vscode.ThemeColor('charts.green'));
        } else if (element.score >= 70) {
            item.iconPath = new vscode.ThemeIcon('warning', new vscode.ThemeColor('charts.yellow'));
        } else {
            item.iconPath = new vscode.ThemeIcon('error', new vscode.ThemeColor('charts.red'));
        }
        
        return item;
    }

    getChildren(element?: VibeResult): VibeResult[] {
        if (!element) {
            return this.vibes;
        }
        return [];
    }
}

class MetricsProvider implements vscode.TreeDataProvider<MetricItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<MetricItem | undefined | null | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
    private metrics: MetricItem[] = [];

    update(result: AnalysisResult) {
        this.metrics = [
            { label: 'Overall Score', value: `${result.overallScore.toFixed(1)}/100` },
            { label: 'Files Analyzed', value: result.filesAnalyzed.toString() },
            { label: 'Lines of Code', value: result.linesAnalyzed.toString() },
            { label: 'Issues Found', value: result.issues.length.toString() },
            { label: 'Analysis Time', value: `${(result.duration / 1000000).toFixed(2)}s` }
        ];
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: MetricItem): vscode.TreeItem {
        const item = new vscode.TreeItem(element.label, vscode.TreeItemCollapsibleState.None);
        item.description = element.value;
        return item;
    }

    getChildren(element?: MetricItem): MetricItem[] {
        if (!element) {
            return this.metrics;
        }
        return [];
    }
}

// Type definitions
interface AnalysisResult {
    overallScore: number;
    filesAnalyzed: number;
    linesAnalyzed: number;
    duration: number;
    issues: Issue[];
    vibeResults: VibeResult[];
    recommendations: string[];
}

interface Issue {
    file: string;
    line: number;
    column?: number;
    severity: string;
    message: string;
    category?: string;
    rule?: string;
    fix?: string;
}

interface VibeResult {
    name: string;
    score: number;
    details?: string;
}

interface MetricItem {
    label: string;
    value: string;
}

// Extension activation
export function activate(context: vscode.ExtensionContext) {
    const extension = new KodeVibeExtension(context);
    context.subscriptions.push(extension);
}

export function deactivate() {}