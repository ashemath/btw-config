#!/bin/sh

if [ !  -d venv ]; then
    echo "Creating venv!";
    python3 -m venv venv;
fi

ansible_test=$(. venv/bin/activate && which ansible);

if [ -z $ansible_test ]; then
    echo "installing ansible in the venv!";
    . venv/bin/activate;
    pip install --upgrade pip;
    pip install ansible;
fi

