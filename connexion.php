<?php
require_once __DIR__ . '/client.php';

$result  = null;
$message = '';
$success = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $pseudo   = trim($_POST['pseudo'] ?? '');
    $password = trim($_POST['password'] ?? '');

    if ($pseudo === '' || $password === '') {
        $message = 'Please fill in all fields.';
    } else {
        $result  = login($pseudo, $password);
        $success = $result['logged_in'];
        $message = $result['message'];
    }
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connexion</title>
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: system-ui, sans-serif;
            background: #f4f6f9;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .card {
            background: #fff;
            border-radius: 10px;
            padding: 2.5rem 2rem;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 4px 20px rgba(0,0,0,.08);
        }
        h1 { font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center; color: #1a1a2e; }
        label { display: block; font-size: .875rem; font-weight: 600; margin-bottom: .35rem; color: #444; }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: .6rem .8rem;
            border: 1px solid #ccc;
            border-radius: 6px;
            font-size: 1rem;
            margin-bottom: 1rem;
            transition: border-color .2s;
        }
        input:focus { outline: none; border-color: #4f6ef7; }
        button[type="submit"] {
            width: 100%;
            padding: .7rem;
            background: #4f6ef7;
            color: #fff;
            border: none;
            border-radius: 6px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background .2s;
        }
        button[type="submit"]:hover { background: #3a57d9; }
        .alert {
            padding: .75rem 1rem;
            border-radius: 6px;
            margin-bottom: 1rem;
            font-size: .9rem;
        }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error   { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .dashboard-link {
            display: block;
            margin-top: 1rem;
            text-align: center;
            color: #4f6ef7;
            font-weight: 600;
            text-decoration: none;
        }
        .dashboard-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Sign In</h1>

        <?php if ($message !== ''): ?>
            <div class="alert <?= $success ? 'alert-success' : 'alert-error' ?>">
                <?= htmlspecialchars($message) ?>
            </div>
        <?php endif; ?>

        <?php if (!$success): ?>
            <form method="POST" action="">
                <label for="pseudo">Pseudo</label>
                <input
                    type="text"
                    id="pseudo"
                    name="pseudo"
                    autocomplete="username"
                    value="<?= htmlspecialchars($_POST['pseudo'] ?? '') ?>"
                    required
                >

                <label for="password">Password</label>
                <input
                    type="password"
                    id="password"
                    name="password"
                    autocomplete="current-password"
                    required
                >

                <button type="submit">Sign In</button>
            </form>
        <?php else: ?>
            <a class="dashboard-link" href="dashboard.php">Go to Dashboard &rarr;</a>
        <?php endif; ?>
    </div>
</body>
</html>
