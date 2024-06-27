<?php
/*
Plugin Name:  Events Exporter
Plugin URI:   https://www.github.com/tschmidty69
Description:  Exports Events from The Event Calendar
Version:      1.0
Author:       Tod Schmidt
Author URI:   https://www.github.com/tschmidty69
License:      GPL3
License URI:  https://www.gnu.org/licenses/gpl-3.0.html
Text Domain:  custom-event-exporter
Domain Path:  custom-event-exporter
*/

function custom_event_export_endpoint() {
    register_rest_route('custom/v1', '/custom-event-exporter/', array(
        'methods' => 'GET',
        'callback' => 'custom_event_export_callback',
        //'permission_callback' =>  '__return_true',
    ));
}
    
function custom_event_export_callback($data) {
    $events = tribe_get_events([
        'start_date'     => 'now',
        'posts_per_page' => 50,
    ]);
    $complete_events = array();
    foreach ($events as $event) {
        $post_meta = tribe_get_event_meta($post_id = $event->ID);
        $merged_event = array_merge($event->to_array(), $post_meta);
        array_push($complete_events, $merged_event);
    }
    return rest_ensure_response($complete_events);
}

add_action('rest_api_init', 'custom_event_export_endpoint');
?>