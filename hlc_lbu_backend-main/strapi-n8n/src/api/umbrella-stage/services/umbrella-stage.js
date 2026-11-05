'use strict';

/**
 * umbrella-stage service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::umbrella-stage.umbrella-stage');
