'use strict';

/**
 * umbrella-resource service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::umbrella-resource.umbrella-resource');
