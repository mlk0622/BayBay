<?php
require_once __DIR__ . '/client.php';

$result = fetch_dashboard();
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard</title>
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: system-ui, sans-serif;
            background: #f4f6f9;
            min-height: 100vh;
            padding: 2rem 1rem;
        }
        .container {
            max-width: 960px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.5rem;
        }
        h1 { font-size: 1.5rem; color: #1a1a2e; }
        .back-link {
            color: #4f6ef7;
            font-size: .875rem;
            text-decoration: none;
            font-weight: 600;
        }
        .back-link:hover { text-decoration: underline; }
        .meta {
            font-size: .8rem;
            color: #888;
            margin-bottom: 1rem;
        }
        .card {
            background: #fff;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0,0,0,.08);
        }
        .alert-error {
            padding: .75rem 1rem;
            border-radius: 6px;
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            font-size: .9rem;
        }
        .response-body {
            white-space: pre-wrap;
            word-break: break-word;
            font-size: .9rem;
            color: #222;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Dashboard</h1>
            <a class="back-link" href="connexion.php">&larr; Back to login</a>
        </div>

        <?php if (!$result['success'] || $result['http_code'] === 0): ?>
            <div class="alert-error">
                Failed to reach the remote server.
                <?php if ($result['error'] !== ''): ?>
                    Details: <?= htmlspecialchars($result['error']) ?>
                <?php endif; ?>
            </div>
        <?php else: ?>
            <p class="meta">HTTP <?= (int)$result['http_code'] ?> &mdash; <?= htmlspecialchars(REMOTE_BASE_URL . '/dashboard.php') ?></p>
            <div class="card">
                <pre class="response-body"><?= htmlspecialchars($result['body']) ?></pre>
            </div>
        <?php endif; ?>
    </div>
</body>
</html>
