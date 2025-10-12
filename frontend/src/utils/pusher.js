// TODO: Replace with your Pusher credentials
import Pusher from 'pusher-js';

export const pusher = new Pusher('YOUR_PUSHER_KEY', {
  cluster: 'YOUR_PUSHER_CLUSTER',
  authEndpoint: '/api/pusher/auth', // If using private/presence channels
});
