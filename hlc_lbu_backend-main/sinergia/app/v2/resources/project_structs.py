AnalyzeMarketingHypothesisStruct = v2_api.model('AnalyzeMarketingHypothesisStruct', { 
    'project_id': fields.Integer(required=True, description='Project ID'),
    'marketing_hypothesis': fields.String(required=True, description='Marketing hypothesis text')
})
