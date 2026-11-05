'use strict';

/**
 * scenario-context service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::scenario-context.scenario-context');
