<?php
require_once __DIR__ . '/ClouDNS_SDK.php';

// Read JSON input from stdin
$inputJSON = file_get_contents('php://stdin');
$input = json_decode($inputJSON, true);

if (!$input) {
    echo json_encode(['failed' => true, 'msg' => 'Invalid JSON input']);
    exit(1);
}

// Extract arguments
$auth_id = $input['auth_id'] ?? null;
$auth_password = $input['auth_password'] ?? null;
$sub_auth_user = $input['sub_auth_user'] ?? false; // true if using sub-user id or username
$is_subuser = (bool) $sub_auth_user;

$action = $input['action'] ?? null;

if (!$auth_id || !$auth_password) {
    echo json_encode(['failed' => true, 'msg' => 'Missing authentication credentials']);
    exit(1);
}

// Initialize SDK
$cloudns = new \ClouDNS\ClouDNS_SDK($auth_id, $auth_password, $is_subuser);

$result = ['changed' => false, 'failed' => false];

try {
    if ($action === 'ensure_record') {
        ensure_record($cloudns, $input, $result);
    } else {
        $result['failed'] = true;
        $result['msg'] = "Unknown action: $action";
    }
} catch (Exception $e) {
    $result['failed'] = true;
    $result['msg'] = $e->getMessage();
}

echo json_encode($result);

function ensure_record($cloudns, $params, &$result) {
    $domain = $params['domain'];
    $host = $params['host'] ?? '';
    $type = $params['type'];
    $value = $params['value'] ?? null;
    $ttl = $params['ttl'] ?? 3600;
    $state = $params['state'] ?? 'present';

    // List existing records for this host and type
    $existing_records = $cloudns->dnsListRecords($domain, $host, $type);

    // Check if API returned an error (SDK usually returns array, if error it might be specific format?)
    // Looking at SDK, it returns json_decode result. If error, usually has 'status' => 'failed' or similar?
    // The SDK doc doesn't specify error format, but let's assume standard behavior.

    if (isset($existing_records['status']) && $existing_records['status'] == 'failed') {
        // If the error is "no records found", we proceed.
        // But the SDK likely returns an empty list or specific message.
        // Let's assume if it fails, we return error, unless it's just "empty".
        // Often 'No records found' is a failure in some APIs.
        if (strpos($existing_records['description'], 'No records found') === false) {
             $result['failed'] = true;
             $result['msg'] = "Failed to list records: " . $existing_records['description'];
             return;
        }
        $existing_records = [];
    }

    // $existing_records is array of records.
    // Structure of record from SDK?
    // From SDK: dnsListRecords returns json_decoded response.
    // Example response structure isn't in SDK code, but typically it is a list of objects (assoc arrays).
    // Let's assume it's a list or a map where keys are IDs.

    // We need to filter exactly matching records.
    // SDK 'host' parameter is optional. If provided, it filters by host.
    // So $existing_records should only contain records for this host and type.

    // However, the return might be wrapped in a key like 'data' or be the array itself.
    // Based on `apiRequest` returning `json_decode($content, true)`, it depends on API.
    // Assuming standard ClouDNS API response.
    // Usually it is an array of records indexed by ID or a list.

    // Let's iterate.
    $matches = [];
    if (is_array($existing_records)) {
        foreach ($existing_records as $rec) {
             // Validate if record matches (host is already filtered by API, type is filtered by API)
             // We just collect them.
             // Note: API might return numeric keys or ID keys.
             if (is_array($rec)) {
                 $matches[] = $rec;
             }
        }
    }

    if ($state === 'present') {
        if (count($matches) == 0) {
            // Add record
            $resp = $cloudns->dnsAddRecord($domain, $type, $host, $value, $ttl);
            if (isset($resp['status']) && $resp['status'] == 'Success') {
                $result['changed'] = true;
                $result['msg'] = "Record added";
                $result['data'] = $resp;
            } else {
                $result['failed'] = true;
                $result['msg'] = "Failed to add record: " . ($resp['description'] ?? 'Unknown error');
            }
        } elseif (count($matches) == 1) {
            // Check if update needed
            $rec = $matches[0];
            $current_value = $rec['record'];
            $current_ttl = $rec['ttl'];
            $record_id = $rec['id'];

            if ($current_value != $value || $current_ttl != $ttl) {
                // Update
                $resp = $cloudns->dnsModifyRecord($domain, $record_id, $host, $value, $ttl);
                if (isset($resp['status']) && $resp['status'] == 'Success') {
                    $result['changed'] = true;
                    $result['msg'] = "Record updated";
                     $result['data'] = $resp;
                } else {
                    $result['failed'] = true;
                    $result['msg'] = "Failed to update record: " . ($resp['description'] ?? 'Unknown error');
                }
            } else {
                $result['msg'] = "Record already exists and matches";
            }
        } else {
            // Multiple records found.
            // If one matches exactly, we are good.
            $exact_match = false;
            foreach ($matches as $rec) {
                if ($rec['record'] == $value && $rec['ttl'] == $ttl) {
                    $exact_match = true;
                    break;
                }
            }
            if ($exact_match) {
                 $result['msg'] = "Record exists (among others)";
            } else {
                $result['failed'] = true;
                $result['msg'] = "Multiple records found for $host $type, none match desired value. ambiguous update.";
            }
        }
    } elseif ($state === 'absent') {
        if (count($matches) > 0) {
            // Remove all matching records? Or just the one with matching value?
            // If value is provided, remove only that one.
            // If value is not provided (or empty?), remove all for this host/type?

            $to_delete = [];
            if ($value) {
                foreach ($matches as $rec) {
                    if ($rec['record'] == $value) {
                        $to_delete[] = $rec['id'];
                    }
                }
            } else {
                // Remove all
                foreach ($matches as $rec) {
                    $to_delete[] = $rec['id'];
                }
            }

            if (count($to_delete) > 0) {
                foreach ($to_delete as $id) {
                    $resp = $cloudns->dnsDeleteRecord($domain, $id);
                    if (isset($resp['status']) && $resp['status'] == 'Success') {
                        $result['changed'] = true;
                    } else {
                         $result['failed'] = true;
                         $result['msg'] = "Failed to delete record $id: " . ($resp['description'] ?? 'Unknown error');
                         return; // Stop on error
                    }
                }
                $result['msg'] = "Records deleted";
            } else {
                $result['msg'] = "Record not found (matching value)";
            }
        } else {
             $result['msg'] = "Record not found";
        }
    }
}
