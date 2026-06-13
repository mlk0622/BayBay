<?php

define('REMOTE_BASE_URL', 'http://88.190.118.23:33080');
define('COOKIE_JAR', __DIR__ . '/session_cookies.txt');

function http_post(string $url, array $fields): array
{
    $ch = curl_init();

    curl_setopt_array($ch, [
        CURLOPT_URL            => $url,
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => http_build_query($fields),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_COOKIEJAR      => COOKIE_JAR,
        CURLOPT_COOKIEFILE     => COOKIE_JAR,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_HTTPHEADER     => [
            'Content-Type: application/x-www-form-urlencoded',
        ],
    ]);

    $body     = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error    = curl_error($ch);
    curl_close($ch);

    return [
        'success'   => $error === '' && $body !== false,
        'http_code' => $httpCode,
        'body'      => $body ?: '',
        'error'     => $error,
    ];
}

function http_get(string $url): array
{
    $ch = curl_init();

    curl_setopt_array($ch, [
        CURLOPT_URL            => $url,
        CURLOPT_HTTPGET        => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_COOKIEJAR      => COOKIE_JAR,
        CURLOPT_COOKIEFILE     => COOKIE_JAR,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_CONNECTTIMEOUT => 10,
    ]);

    $body     = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error    = curl_error($ch);
    curl_close($ch);

    return [
        'success'   => $error === '' && $body !== false,
        'http_code' => $httpCode,
        'body'      => $body ?: '',
        'error'     => $error,
    ];
}

function login(string $pseudo, string $password): array
{
    $url    = REMOTE_BASE_URL . '/connexion.php';
    $result = http_post($url, [
        'pseudo'   => $pseudo,
        'password' => $password,
    ]);

    if (!$result['success']) {
        return [
            'logged_in' => false,
            'message'   => 'Connection error: ' . $result['error'],
        ];
    }

    $loginFailed = stripos($result['body'], 'invalid') !== false
        || stripos($result['body'], 'incorrect') !== false
        || stripos($result['body'], 'error') !== false
        || stripos($result['body'], 'failed') !== false
        || stripos($result['body'], 'wrong') !== false;

    if ($loginFailed) {
        return [
            'logged_in' => false,
            'message'   => 'Invalid credentials.',
        ];
    }

    return [
        'logged_in' => true,
        'message'   => 'Login successful.',
        'body'      => $result['body'],
    ];
}

function fetch_dashboard(): array
{
    $url = REMOTE_BASE_URL . '/dashboard.php';
    return http_get($url);
}

function dashboard_post(array $fields): array
{
    $url = REMOTE_BASE_URL . '/dashboard.php';
    return http_post($url, $fields);
}
