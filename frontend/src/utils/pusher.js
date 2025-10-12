// TODO: Replace with your Pusher credentials
import Pusher from 'pusher-js';

export const pusher = new Pusher('YOUR_PUSHER_KEY', {
  cluster: 'us2',
  authEndpoint: '/api/pusher/auth', // If using private/presence channels
});
