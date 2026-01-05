build-SendMessageFunction:
	@echo "Building SendMessageFunction..."
	# Copy commons directory to function package
	cp -r ../../commons $(ARTIFACTS_DIR)/ || echo "Warning: Could not copy commons"
	# Copy function code
	cp app.py $(ARTIFACTS_DIR)/
	@echo "Build complete for SendMessageFunction"
