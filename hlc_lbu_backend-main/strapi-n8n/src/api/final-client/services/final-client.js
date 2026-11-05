'use strict';

/**
 * final-client service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::final-client.final-client');
