<?php
/**
 * Plugin Name: Event Announcement Posts
 * Description: Automatically generates blog posts from Events Calendar events + manual generate button.
 * Version: 1.0
 */

if (!defined('ABSPATH')) exit;

/**
 * MAIN FUNCTION: create or update announcement post
 */
function eap_create_or_update_announcement($event_id) {

    $event = get_post($event_id);
    if (!$event || $event->post_type !== 'tribe_events') return;

    // prevent duplicates
    $existing_post_id = get_post_meta($event_id, '_eap_linked_post_id', true);

    // event start date (Events Calendar meta)
    $start = get_post_meta($event_id, '_EventStartDate', true);
    if (!$start) return;

    $publish_ts = strtotime($start . ' -2 days');

    // fallback: if already past, publish immediately
    $status = ($publish_ts <= time()) ? 'publish' : 'future';

    $post_data = [
        'post_title'   => $event->post_title,
        'post_content' =>
            '<p><a href="' . get_permalink($event_id) . '"><h2>Click here to view the live stream or recording.<h2></a></p>'.
            '<p>' . $event->post_content . '</p>',
        'post_type'    => 'post',
        'post_status'  => $status,
        'post_date'    => date('Y-m-d H:i:s', $publish_ts),
    ];

    // create or update
    if ($existing_post_id && get_post($existing_post_id)) {
        $post_data['ID'] = $existing_post_id;
        wp_update_post($post_data);
        $post_id = $existing_post_id;
    } else {
        $post_id = wp_insert_post($post_data);
        update_post_meta($event_id, '_eap_linked_post_id', $post_id);
        update_post_meta($post_id, '_eap_linked_event_id', $event_id);
    }

    // copy featured image
    $thumb = get_post_thumbnail_id($event_id);
    if ($thumb) {
        set_post_thumbnail($post_id, $thumb);
    }

    return $post_id;
}

add_action('transition_post_status', function($new, $old, $post) {

    if ($post->post_type !== 'tribe_events') return;
    if ($old === 'publish' || $new !== 'publish') return;

    eap_create_or_update_announcement($post->ID);

}, 10, 3);

add_action('admin_post_eap_generate', function() {

    if (!current_user_can('edit_posts')) {
        wp_die('Not allowed');
    }

    $event_id = intval($_GET['event_id'] ?? 0);
    if (!$event_id) wp_die('Missing event ID');

    eap_create_or_update_announcement($event_id);

    wp_redirect(admin_url('post.php?post=' . $event_id . '&action=edit&eap=done'));
    exit;
});

add_action('add_meta_boxes', function() {

    add_meta_box(
        'eap_box',
        'Event Announcement Post',
        function($post) {

            if ($post->post_type !== 'tribe_events') return;

            $linked = get_post_meta($post->ID, '_eap_linked_post_id', true);

            if ($linked && get_post($linked)) {

                echo '<p><strong>Announcement exists.</strong></p>';
                echo '<p><a href="' . get_edit_post_link($linked) . '">Edit Post</a></p>';

                echo '<p><a href="' . admin_url('admin-post.php?action=eap_generate&event_id=' . $post->ID) . '">
                Regenerate Announcement</a></p>';

            } else {

                echo '<p>No announcement post yet.</p>';

                echo '<p><a class="button button-primary"
                href="' . admin_url('admin-post.php?action=eap_generate&event_id=' . $post->ID) . '">
                Generate Announcement Post</a></p>';
            }
        },
        'tribe_events',
        'side',
        'default'
    );

});